from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any


POLITICAL_STABILITY_TERMS = (
    "protest",
    "protests",
    "protester",
    "protesters",
    "protesting",
    "protested",
    "demonstration",
    "demonstrations",
    "civil unrest",
    "riot",
    "riots",
    "rioting",
    "labor strike",
    "workers strike",
    "general strike",
    "government collapse",
    "cabinet collapse",
    "coalition collapse",
    "regime",
    "succession",
    "leadership transition",
    "elite split",
    "elite cohesion",
    "political instability",
    "constitutional crisis",
    "impeachment",
    "election",
    "elections",
    "vote",
    "votes",
    "voted",
    "voting",
    "opposition",
    "opposition leader",
    "opposition leaders",
    "dissident",
    "dissidents",
    "repression",
    "arrested opposition",
    "state legitimacy",
    "governance crisis",
    "coup",
    "mutiny",
    "defection",
)

CONFLICT_ONLY_TERMS = (
    "airstrike",
    "air strike",
    "missile strike",
    "military strike",
    "naval strike",
    "forces strike",
    "strikes iran",
    "missile barrage",
    "retaliatory strike",
    "ceasefire crumbles",
    "kinetic conflict",
    "shipping crisis",
    "strait of hormuz",
    "oil shipment",
    "energy security",
    "petrochemical plant",
    "petrochemical site",
)


def _phrase_matches(
    text: str,
    term: str,
) -> bool:
    """
    Match complete words/phrases rather than arbitrary substrings.

    This prevents false positives such as:
        "vote" matching "devotees"
    """
    pattern = (
        r"(?<![a-z0-9])"
        + re.escape(term.lower())
        + r"(?![a-z0-9])"
    )

    return bool(re.search(pattern, text))


def _is_political_stability_relevant(text: str) -> bool:
    normalized = " ".join(
        str(text or "").lower().split()
    )

    political_match = any(
        _phrase_matches(normalized, term)
        for term in POLITICAL_STABILITY_TERMS
    )

    conflict_only_match = any(
        _phrase_matches(normalized, term)
        for term in CONFLICT_ONLY_TERMS
    )

    return political_match and not conflict_only_match

import httpx

from app.agents.base_agent import AgentSignal


INTERNAL_API_BASE_URL = os.getenv(
    "STRATEGIC_INTERNAL_API_BASE_URL",
    "http://127.0.0.1:8000",
).rstrip("/")


POLITICAL_PATTERNS = (
    r"\belection(s)?\b",
    r"\bvote(s|d|r)?\b",
    r"\bprotest(s|ed|ing)?\b",
    r"\bdemonstration(s)?\b",
    r"\briot(s|ing)?\b",
    r"\bstrike(s|rs|ing)?\b",
    r"\bcoup\b",
    r"\bgovernment collapse\b",
    r"\bcabinet collapse\b",
    r"\bprime minister resign",
    r"\bpresident resign",
    r"\bminister resign",
    r"\bresignation\b",
    r"\bimpeach",
    r"\bconstitutional crisis\b",
    r"\bemergency declaration\b",
    r"\bstate of emergency\b",
    r"\bparliament dissolv",
    r"\bcoalition collapse\b",
    r"\bgovernment instability\b",
    r"\bpolitical instability\b",
    r"\belite defection\b",
    r"\bmilitary takeover\b",
    r"\bmartial law\b",
    r"\binternet shutdown\b",
    r"\bopposition leader\b",
    r"\bpolitical assassination\b",
    r"\belection violence\b",
    r"\bpublic sector strike\b",
)


DETERIORATION_PATTERNS = (
    r"\bcoup\b",
    r"\briot",
    r"\bviolence\b",
    r"\bgovernment collapse\b",
    r"\bcabinet collapse\b",
    r"\bconstitutional crisis\b",
    r"\bstate of emergency\b",
    r"\bmartial law\b",
    r"\bpolitical assassination\b",
    r"\binternet shutdown\b",
    r"\bimpeach",
    r"\bresign",
    r"\bprotest",
    r"\bstrike",
)


IMPROVEMENT_PATTERNS = (
    r"\bpeaceful election\b",
    r"\bcoalition agreement\b",
    r"\bgovernment formed\b",
    r"\btransition completed\b",
    r"\bconstitutional settlement\b",
    r"\bprotests end\b",
    r"\bstrike ends\b",
)


SOURCE_RELIABILITY = {
    "reuters": 92,
    "associated press": 91,
    "financial times": 89,
    "bloomberg": 88,
    "bbc": 87,
    "the economist": 87,
    "new york times": 86,
    "washington post": 85,
    "wall street journal": 85,
    "foreign affairs": 84,
    "al jazeera": 79,
    "radio free europe/radio liberty": 80,
    "south china morning post": 76,
    "taipei times": 76,
    "msn": 58,
    "google news rss": 65,
}


SEVERITY_MAP = {
    "critical": 90,
    "high": 78,
    "elevated": 66,
    "warning": 58,
    "watch": 45,
    "monitoring": 35,
    "moderate": 50,
    "low": 25,
}


KNOWN_PUBLISHERS = tuple(
    name.title()
    for name in SOURCE_RELIABILITY
    if name not in {"google news rss"}
)


def _contains_political_language(text: str) -> bool:
    """
    Use the canonical political-stability relevance taxonomy.

    This prevents the normalization gate and final relevance filter
    from using different political vocabularies.
    """
    return _is_political_stability_relevant(text)


def _infer_direction(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.lower()).strip()

    if any(re.search(pattern, normalized) for pattern in IMPROVEMENT_PATTERNS):
        return "improving"

    if any(re.search(pattern, normalized) for pattern in DETERIORATION_PATTERNS):
        return "deteriorating"

    return "neutral"


def _source_reliability(source: str | None) -> float:
    normalized = (source or "").strip().lower()

    for name, score in SOURCE_RELIABILITY.items():
        if name in normalized:
            return float(score)

    return 60.0


def _extract_original_publisher(title: str, source: str | None) -> str:
    normalized_source = (source or "").strip()

    if normalized_source.lower() not in {
        "google news rss",
        "googlerss",
        "google news",
    }:
        return normalized_source or "internal_signal_store"

    for publisher in KNOWN_PUBLISHERS:
        suffix = f" - {publisher}"
        if title.endswith(suffix):
            return publisher

    return normalized_source or "Google News RSS"


def _severity_to_score(value: Any, fallback: float = 40) -> float:
    if isinstance(value, (int, float)):
        return float(max(0, min(100, value)))

    normalized = str(value or "").strip().lower()

    if normalized in SEVERITY_MAP:
        return float(SEVERITY_MAP[normalized])

    try:
        return float(max(0, min(100, float(normalized))))
    except (TypeError, ValueError):
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
        (datetime.now(timezone.utc) - event_time).total_seconds() / 3600,
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


def _country_matches(
    item: dict[str, Any],
    country_name: str | None,
    country_iso3: str | None,
) -> bool:
    if not country_name and not country_iso3:
        return True

    searchable = " ".join(
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

    if country_name and country_name.lower() in searchable:
        return True

    return (
        bool(country_iso3)
        and str(item.get("country_iso3") or "").upper()
        == country_iso3.upper()
    )


def _normalize_signal(
    item: dict[str, Any],
    *,
    country_name: str | None,
    country_iso3: str | None,
    region: str | None,
    source_mode: str,
) -> AgentSignal | None:
    title = str(item.get("title") or item.get("headline") or "").strip()
    summary = str(item.get("summary") or "").strip()
    domain = str(
        item.get("signal_domain")
        or item.get("domain")
        or ""
    ).lower()

    combined_text = f"{title} {summary} {domain}"

    if not _contains_political_language(combined_text):
        return None

    # Country-intelligence results are already scoped by the
    # requested country endpoint. Requiring the article text to repeat
    # the country name incorrectly rejects valid country-specific news.
    #
    # Global/internal signal-store results still require an explicit
    # country match to prevent cross-country contamination.
    if (
        source_mode != "country_intelligence"
        and not _country_matches(
            item,
            country_name,
            country_iso3,
        )
    ):
        return None

    event_time = (
        item.get("published_at")
        or item.get("event_time")
        or item.get("created_at")
    )
    freshness = _freshness_factor(str(event_time or ""))

    raw_severity = _severity_to_score(
        item.get("signal_score") or item.get("severity"),
        fallback=40,
    )
    severity = round(raw_severity * freshness, 2)

    source = _extract_original_publisher(
        title,
        str(
            item.get("source")
            or item.get("provider")
            or source_mode
        ),
    )
    reliability = _source_reliability(source)

    confidence = _severity_to_score(
        item.get("confidence"),
        fallback=round(55 + reliability * 0.25, 2),
    )

    relevance = 92 if country_name or country_iso3 else 72

    materiality = round(
        severity * 0.45
        + confidence * 0.20
        + reliability * 0.20
        + relevance * 0.15,
        2,
    )

    return AgentSignal(
        signal_id=str(
            item.get("id")
            or item.get("signal_id")
            or f"political-{abs(hash(title))}"
        ),
        domain="political",
        signal_type="political_stability_event",
        headline=title or "Political stability signal",
        summary=summary or None,
        country_iso3=country_iso3,
        country_name=country_name,
        region=region,
        severity=severity,
        relevance=relevance,
        confidence=confidence,
        source_reliability=reliability,
        materiality_score=materiality,
        direction=_infer_direction(combined_text),
        event_time=str(event_time) if event_time else None,
        source_key=source,
        evidence_url=item.get("url"),
        indicators=[
            {
                "name": "freshness_factor",
                "value": freshness,
            }
        ],
        tags=[domain] if domain else [],
    )


async def collect_live_political_signals(
    *,
    country_name: str | None = None,
    country_iso3: str | None = None,
    region: str | None = None,
    limit: int = 25,
) -> list[AgentSignal]:
    signals: list[AgentSignal] = []

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            response = await client.get(
                f"{INTERNAL_API_BASE_URL}/api/signals/latest"
            )
            response.raise_for_status()

            for item in response.json().get("signals", []):
                normalized = _normalize_signal(
                    item,
                    country_name=country_name,
                    country_iso3=country_iso3,
                    region=region,
                    source_mode="internal_signal_store",
                )
                if normalized:
                    signals.append(normalized)

        except Exception:
            pass

        if country_name:
            try:
                response = await client.get(
                    f"{INTERNAL_API_BASE_URL}/api/country-intelligence/"
                    f"debug/signals/{country_name}"
                )
                response.raise_for_status()

                for item in response.json().get("data", []):
                    normalized = _normalize_signal(
                        item,
                        country_name=country_name,
                        country_iso3=country_iso3,
                        region=region,
                        source_mode="country_intelligence",
                    )
                    if normalized:
                        signals.append(normalized)

            except Exception:
                pass

    deduplicated: dict[str, AgentSignal] = {}

    for signal in signals:
        key = re.sub(
            r"[^a-z0-9]+",
            " ",
            signal.headline.lower(),
        ).strip()

        existing = deduplicated.get(key)

        if (
            existing is None
            or signal.materiality_score > existing.materiality_score
        ):
            deduplicated[key] = signal

    filtered = []

    for signal in deduplicated.values():
        combined = " ".join(
            str(value or "")
            for value in (
                signal.headline,
                signal.summary,
                signal.signal_type,
            )
        )

        if _is_political_stability_relevant(combined):
            filtered.append(signal)

    return sorted(
        filtered,
        key=lambda item: (
            item.materiality_score,
            item.severity,
            item.confidence,
        ),
        reverse=True,
    )[:limit]
