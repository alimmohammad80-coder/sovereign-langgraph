from __future__ import annotations

import csv
import io
import re
import threading
from datetime import datetime, timezone
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


OFAC_SDN_CSV = "https://www.treasury.gov/ofac/downloads/sdn.csv"

OFAC_CACHE_TTL_SECONDS = 8 * 60 * 60
OFAC_REQUEST_TIMEOUT = (8, 45)

_cache_lock = threading.Lock()
_cached_csv_text: str | None = None
_cached_downloaded_at: datetime | None = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _cache_age_seconds(
    now: datetime | None = None,
) -> float | None:
    if _cached_downloaded_at is None:
        return None

    current = now or _utc_now()

    return max(
        0.0,
        (current - _cached_downloaded_at).total_seconds(),
    )


def _cache_is_fresh(
    now: datetime | None = None,
) -> bool:
    age = _cache_age_seconds(now)

    return bool(
        _cached_csv_text is not None
        and age is not None
        and age < OFAC_CACHE_TTL_SECONDS
    )


def _build_session() -> requests.Session:
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=1.0,
        status_forcelist=(
            429,
            500,
            502,
            503,
            504,
        ),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
        raise_on_status=False,
    )

    adapter = HTTPAdapter(
        max_retries=retry,
        pool_connections=4,
        pool_maxsize=4,
    )

    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    session.headers.update(
        {
            "User-Agent": (
                "Sovereign-Intelligence-AI/1.0 "
                "(OFAC sanctions screening)"
            ),
            "Accept": "text/csv,*/*",
        }
    )

    return session


def _load_ofac_csv() -> dict[str, Any]:
    global _cached_csv_text
    global _cached_downloaded_at

    now = _utc_now()

    if _cache_is_fresh(now):
        return {
            "status": "cache_fresh",
            "csv_text": _cached_csv_text,
            "downloaded_at": (
                _cached_downloaded_at.isoformat()
                if _cached_downloaded_at
                else None
            ),
            "cache_age_seconds": _cache_age_seconds(now),
            "download_error": None,
        }

    with _cache_lock:
        now = _utc_now()

        if _cache_is_fresh(now):
            return {
                "status": "cache_fresh",
                "csv_text": _cached_csv_text,
                "downloaded_at": (
                    _cached_downloaded_at.isoformat()
                    if _cached_downloaded_at
                    else None
                ),
                "cache_age_seconds": _cache_age_seconds(now),
                "download_error": None,
            }

        session = _build_session()

        try:
            response = session.get(
                OFAC_SDN_CSV,
                timeout=OFAC_REQUEST_TIMEOUT,
            )
            response.raise_for_status()

            csv_text = response.content.decode(
                "utf-8-sig",
                errors="replace",
            )

            if not csv_text.strip():
                raise ValueError("OFAC SDN CSV response was empty")

            _cached_csv_text = csv_text
            _cached_downloaded_at = _utc_now()

            return {
                "status": "downloaded",
                "csv_text": csv_text,
                "downloaded_at": (
                    _cached_downloaded_at.isoformat()
                ),
                "cache_age_seconds": 0.0,
                "download_error": None,
            }

        except Exception as exc:
            if _cached_csv_text is not None:
                return {
                    "status": "cache_stale_fallback",
                    "csv_text": _cached_csv_text,
                    "downloaded_at": (
                        _cached_downloaded_at.isoformat()
                        if _cached_downloaded_at
                        else None
                    ),
                    "cache_age_seconds": _cache_age_seconds(),
                    "download_error": str(exc),
                }

            return {
                "status": "error",
                "csv_text": None,
                "downloaded_at": None,
                "cache_age_seconds": None,
                "download_error": str(exc),
            }

        finally:
            session.close()


def _normalize(value: Any) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(value or "").strip().lower(),
    )


def _whole_term_match(text: str, term: str) -> bool:
    normalized_text = _normalize(text)
    normalized_term = _normalize(term)

    if not normalized_term:
        return False

    pattern = (
        r"(?<![a-z0-9])"
        + re.escape(normalized_term)
        + r"(?![a-z0-9])"
    )

    return bool(
        re.search(
            pattern,
            normalized_text,
            flags=re.IGNORECASE,
        )
    )


def _clean_field(value: Any) -> str | None:
    cleaned = str(value or "").strip()

    if not cleaned or cleaned == "-0-":
        return None

    return cleaned


def _extract_programs(program_field: str | None) -> list[str]:
    if not program_field:
        return []

    normalized = str(program_field).strip()

    # OFAC CSV program fields may omit the opening bracket
    # on the first program and the closing bracket on the last.
    fragments = re.split(r"\]\s*\[|\]|\[", normalized)

    programs = []

    for fragment in fragments:
        cleaned = fragment.strip()

        if not cleaned:
            continue

        if re.fullmatch(r"[A-Z0-9_-]+", cleaned):
            programs.append(cleaned)

    return list(dict.fromkeys(programs))


def fetch_ofac_sdn_matches(
    country: str | None = None,
    commodity: str | None = None,
    sector: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    search_terms = [
        term.strip()
        for term in (country, commodity, sector)
        if term and term.strip()
    ]

    if not search_terms:
        return {
            "ofac_sanctions_signal": False,
            "sanctions_matches": [],
            "ofac_status": "no_search_terms",
            "checked_at": _utc_now().isoformat(),
        }

    source_result = _load_ofac_csv()
    checked_at = _utc_now().isoformat()

    csv_text = source_result.get("csv_text")

    if not csv_text:
        return {
            "ofac_sanctions_signal": False,
            "sanctions_matches": [],
            "ofac_status": (
                f"error: {source_result.get('download_error')}"
            ),
            "source_status": source_result.get("status"),
            "source_downloaded_at": None,
            "cache_age_seconds": None,
            "checked_at": checked_at,
        }

    reader = csv.reader(io.StringIO(csv_text))

    matches: list[dict[str, Any]] = []

    for row in reader:
        if not row:
            continue

        searchable_text = " | ".join(
            str(field or "")
            for field in row
        )

        matched_terms = [
            term
            for term in search_terms
            if _whole_term_match(searchable_text, term)
        ]

        if not matched_terms:
            continue

        uid = _clean_field(
            row[0] if len(row) > 0 else None
        )
        entity_name = _clean_field(
            row[1] if len(row) > 1 else None
        )
        sdn_type = _clean_field(
            row[2] if len(row) > 2 else None
        )
        program_field = _clean_field(
            row[3] if len(row) > 3 else None
        )

        matches.append(
            {
                "uid": uid,
                "entity_name": entity_name,
                "sdn_type": sdn_type,
                "programs": _extract_programs(
                    program_field
                ),
                "program_field": program_field,
                "matched_terms": matched_terms,
                "source": "OFAC SDN List",
                "raw_record": row,
            }
        )

        if len(matches) >= max(1, limit):
            break

    return {
        "ofac_sanctions_signal": bool(matches),
        "sanctions_matches": matches,
        "ofac_status": "connected",
        "source_status": source_result.get("status"),
        "source_downloaded_at": source_result.get(
            "downloaded_at"
        ),
        "cache_age_seconds": source_result.get(
            "cache_age_seconds"
        ),
        "download_error": source_result.get(
            "download_error"
        ),
        "query": {
            "country": country,
            "commodity": commodity,
            "sector": sector,
        },
        "checked_at": checked_at,
    }
