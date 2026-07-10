from __future__ import annotations

import asyncio
import hashlib
import os
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from app.agents.base_agent import AgentSignal
from services.supply_chain_ofac import fetch_ofac_sdn_matches


INTERNAL_API_BASE_URL = os.getenv(
    "STRATEGIC_INTERNAL_API_BASE_URL",
    "http://127.0.0.1:8000",
).rstrip("/")


TRADE_SANCTIONS_PATTERNS = (
    r"\bsanction(s|ed|ing)?\b",
    r"\bsecondary sanctions\b",
    r"\bexport control(s)?\b",
    r"\bexport restriction(s)?\b",
    r"\bimport ban\b",
    r"\bexport ban\b",
    r"\bembargo\b",
    r"\btariff(s)?\b",
    r"\btrade restriction(s)?\b",
    r"\btrade barrier(s)?\b",
    r"\bblacklist(ed|ing)?\b",
    r"\bentity list\b",
    r"\btechnology controls\b",
    r"\blicensing restriction(s)?\b",
    r"\bcustoms restriction(s)?\b",
    r"\btrade war\b",
)


DETERIORATING_PATTERNS = (
    r"\bnew sanctions\b",
    r"\badditional sanctions\b",
    r"\bsanctions imposed\b",
    r"\bsanctions expanded\b",
    r"\bexport controls tightened\b",
    r"\bexport ban\b",
    r"\bimport ban\b",
    r"\bembargo\b",
    r"\btariff increase\b",
    r"\btrade restrictions imposed\b",
    r"\bblacklisted\b",
)


IMPROVING_PATTERNS = (
    r"\bsanctions lifted\b",
    r"\bsanctions eased\b",
    r"\bsanctions relief\b",
    r"\bwaiver granted\b",
    r"\bexport restrictions eased\b",
    r"\btariffs reduced\b",
    r"\btrade agreement\b",
)


SEVERITY_MAP = {
    "critical": 90,
    "high": 78,
    "elevated": 65,
    "warning": 58,
    "watch": 45,
    "monitoring": 35,
    "moderate": 50,
    "low": 25,
}


SOURCE_RELIABILITY = {
    "reuters": 92,
    "associated press": 91,
    "financial times": 89,
    "bloomberg": 88,
    "wall street journal": 86,
    "bbc": 87,
    "new york times": 85,
    "washington post": 84,
    "al jazeera": 79,
    "south china morning post": 76,
    "google news rss": 65,
    "ofac sdn list": 98,
}


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}-{digest}"


def _contains_trade_sanctions_language(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.lower()).strip()
    return any(
        re.search(pattern, normalized)
        for pattern in TRADE_SANCTIONS_PATTERNS
    )


def _infer_direction(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.lower()).strip()

    if any(
        re.search(pattern, normalized)
        for pattern in IMPROVING_PATTERNS
    ):
        return "improving"

    if any(
        re.search(pattern, normalized)
        for pattern in DETERIORATING_PATTERNS
    ):
        return "deteriorating"

    return "neutral"


def _source_reliability(source: str | None) -> float:
    normalized = str(source or "").strip().lower()

    for name, score in SOURCE_RELIABILITY.items():
        if name in normalized:
            return float(score)

    return 62.0


def _severity_score(value: Any, fallback: float = 40) -> float:
    if isinstance(value, (int, float)):
        numeric = float(value)

        if numeric <= 10:
            numeric *= 10

        return max(0, min(100, numeric))

    normalized = str(value or "").strip().lower()

    if normalized in SEVERITY_MAP:
        return float(SEVERITY_MAP[normalized])

    return fallback


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        pass

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _freshness_factor(value: str | None) -> float:
    event_time = _parse_datetime(value)

    if event_time is None:
        return 0.65

    age_hours = max(
        0,
        (
            datetime.now(timezone.utc) - event_time
        ).total_seconds() / 3600,
    )

    if age_hours <= 24:
        return 1.0
    if age_hours <= 72:
        return 0.90
    if age_hours <= 168:
        return 0.75
    if age_hours <= 336:
        return 0.55
    return 0.30


def _extract_publisher(title: str, source: str | None) -> str:
    normalized_source = str(source or "").strip()

    if normalized_source.lower() not in {
        "google news rss",
        "google news",
    }:
        return normalized_source or "Country Intelligence"

    if " - " in title:
        candidate = title.rsplit(" - ", 1)[-1].strip()
        if candidate:
            return candidate

    return normalized_source or "Google News RSS"


def _ofac_signals(
    result: dict[str, Any],
    *,
    country_name: str,
    country_iso3: str | None,
    region: str | None,
) -> list[AgentSignal]:
    matches = result.get("sanctions_matches") or []

    if not matches:
        return []

    financial_count = 0
    defense_count = 0
    individual_count = 0

    for match in matches:
        name = str(match.get("entity_name") or "").lower()
        sdn_type = str(match.get("sdn_type") or "").lower()
        programs = " ".join(match.get("programs") or []).lower()

        if "bank" in name or "financial" in name:
            financial_count += 1

        if any(
            term in name or term in programs
            for term in (
                "defense",
                "aerospace",
                "armed forces",
                "irgc",
                "npwmd",
            )
        ):
            defense_count += 1

        if sdn_type == "individual":
            individual_count += 1

    match_count = len(matches)

    # This represents sanctions exposure, not a new sanctions event.
    severity = min(
        85.0,
        45.0
        + min(20.0, match_count * 1.5)
        + min(10.0, financial_count * 2.0)
        + min(10.0, defense_count * 1.5),
    )

    top_entities = [
        str(match.get("entity_name") or "Unnamed entity")
        for match in matches[:6]
    ]

    return [
        AgentSignal(
            signal_id=_stable_id(
                "ofac-country-exposure",
                f"{country_name}-{'|'.join(top_entities)}",
            ),
            domain="trade_sanctions",
            signal_type="country_sanctions_exposure",
            headline=(
                f"OFAC screening identified {match_count} country-linked "
                f"SDN records associated with {country_name}"
            ),
            summary=(
                f"Country-linked screening results include: "
                f"{', '.join(top_entities)}. "
                f"Financial-sector records: {financial_count}; "
                f"defense/security records: {defense_count}; "
                f"individual records: {individual_count}. "
                f"These results indicate structural screening exposure and "
                f"are not a determination that an unlisted counterparty, "
                f"transaction, or affiliate is blocked."
            ),
            country_iso3=country_iso3,
            country_name=country_name,
            region=region,
            severity=severity,
            relevance=98,
            confidence=95,
            source_reliability=98,
            materiality_score=round(
                severity * 0.50
                + 98 * 0.20
                + 95 * 0.15
                + 98 * 0.15,
                2,
            ),
            direction="neutral",
            source_key="OFAC SDN List",
            indicators=[
                {
                    "name": "ofac_match_count",
                    "value": match_count,
                },
                {
                    "name": "financial_sector_matches",
                    "value": financial_count,
                },
                {
                    "name": "defense_security_matches",
                    "value": defense_count,
                },
            ],
            tags=["sanctions", "ofac", "structural_exposure"],
        )
    ]


def _normalize_news_signal(
    item: dict[str, Any],
    *,
    country_name: str,
    country_iso3: str | None,
    region: str | None,
) -> AgentSignal | None:
    title = str(item.get("title") or item.get("headline") or "").strip()
    summary = str(item.get("summary") or "").strip()
    domain = str(
        item.get("signal_domain")
        or item.get("domain")
        or ""
    ).lower()

    combined = f"{title} {summary} {domain}"

    if not _contains_trade_sanctions_language(combined):
        return None

    published_at = (
        item.get("published_at")
        or item.get("event_time")
        or item.get("created_at")
    )

    freshness = _freshness_factor(str(published_at or ""))

    raw_severity = _severity_score(
        item.get("severity")
        or item.get("severity_score"),
        fallback=42,
    )

    severity = round(raw_severity * freshness, 2)

    source = _extract_publisher(
        title,
        item.get("source") or item.get("source_name"),
    )

    reliability = _source_reliability(source)
    confidence = min(92.0, 55.0 + reliability * 0.30)

    return AgentSignal(
        signal_id=_stable_id(
            "trade-news",
            f"{country_name}-{title}",
        ),
        domain="trade_sanctions",
        signal_type="trade_sanctions_event",
        headline=title,
        summary=summary or None,
        country_iso3=country_iso3,
        country_name=country_name,
        region=region,
        severity=severity,
        relevance=92,
        confidence=confidence,
        source_reliability=reliability,
        materiality_score=round(
            severity * 0.50
            + 92 * 0.20
            + confidence * 0.15
            + reliability * 0.15,
            2,
        ),
        direction=_infer_direction(combined),
        event_time=str(published_at) if published_at else None,
        source_key=source,
        evidence_url=item.get("url") or item.get("source_url"),
        tags=["trade", "sanctions", domain] if domain else ["trade", "sanctions"],
    )


async def collect_live_trade_sanctions_signals(
    *,
    country_name: str,
    country_iso3: str | None = None,
    region: str | None = None,
    commodity: str | None = None,
    sector: str | None = None,
    limit: int = 25,
) -> list[AgentSignal]:
    signals: list[AgentSignal] = []

    ofac_result = await asyncio.to_thread(
        fetch_ofac_sdn_matches,
        country_name,
        commodity,
        sector,
        25,
    )

    signals.extend(
        _ofac_signals(
            ofac_result,
            country_name=country_name,
            country_iso3=country_iso3,
            region=region,
        )
    )

    async with httpx.AsyncClient(timeout=25.0) as client:
        try:
            response = await client.get(
                f"{INTERNAL_API_BASE_URL}/api/country-intelligence/"
                f"debug/signals/{country_name}"
            )
            response.raise_for_status()

            for item in response.json().get("data", []):
                normalized = _normalize_news_signal(
                    item,
                    country_name=country_name,
                    country_iso3=country_iso3,
                    region=region,
                )

                if normalized:
                    signals.append(normalized)

        except Exception:
            pass

        try:
            response = await client.get(
                f"{INTERNAL_API_BASE_URL}/api/signals/latest"
            )
            response.raise_for_status()

            for item in response.json().get("signals", []):
                text = " ".join(
                    str(item.get(field) or "")
                    for field in (
                        "title",
                        "headline",
                        "summary",
                        "country",
                        "country_name",
                        "country_iso3",
                    )
                ).lower()

                if (
                    country_name.lower() not in text
                    and (
                        not country_iso3
                        or country_iso3.lower() not in text
                    )
                ):
                    continue

                normalized = _normalize_news_signal(
                    item,
                    country_name=country_name,
                    country_iso3=country_iso3,
                    region=region,
                )

                if normalized:
                    signals.append(normalized)

        except Exception:
            pass

    deduplicated: dict[str, AgentSignal] = {}

    for signal in signals:
        current = deduplicated.get(signal.signal_id)

        if (
            current is None
            or signal.materiality_score > current.materiality_score
        ):
            deduplicated[signal.signal_id] = signal

    return sorted(
        deduplicated.values(),
        key=lambda item: (
            item.materiality_score,
            item.severity,
            item.confidence,
        ),
        reverse=True,
    )[:limit]
