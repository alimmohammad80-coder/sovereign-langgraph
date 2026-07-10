from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from app.agents.base_agent import AgentSignal


INTERNAL_API_BASE_URL = os.getenv(
    "STRATEGIC_INTERNAL_API_BASE_URL",
    "http://127.0.0.1:8000",
).rstrip("/")


CONFLICT_KEYWORDS = (
    "airstrike",
    "armed clash",
    "artillery",
    "attack",
    "ballistic missile",
    "blockade",
    "border incident",
    "ceasefire",
    "coast guard",
    "conflict",
    "drone",
    "exercise",
    "forces",
    "invasion",
    "kinetic",
    "maritime patrol",
    "military",
    "missile",
    "mobilization",
    "naval",
    "patrol",
    "pla",
    "rocket",
    "strike",
    "troop",
    "warship",
    "weapons",
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


KNOWN_PUBLISHERS = (
    "Reuters",
    "Associated Press",
    "AP News",
    "Financial Times",
    "Bloomberg",
    "BBC",
    "The Economist",
    "The New York Times",
    "The Washington Post",
    "The Wall Street Journal",
    "Foreign Affairs",
    "Radio Free Europe/Radio Liberty",
    "South China Morning Post",
    "Taipei Times",
    "MSN",
)


def _extract_original_publisher(
    title: str,
    source: str | None,
) -> str:
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


def _source_reliability(source: str | None) -> float:
    normalized = (source or "").strip().lower()

    for name, score in SOURCE_RELIABILITY.items():
        if name in normalized:
            return float(score)

    return 60.0


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
    return 0.35


def _contains_conflict_language(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.lower()).strip()

    patterns = (
        r"\bair\s*strike(s)?\b",
        r"\barmed clash(es)?\b",
        r"\bartillery\b",
        r"\battack(s|ed|ing)?\b",
        r"\bballistic missile(s)?\b",
        r"\bblockade\b",
        r"\bborder incident(s)?\b",
        r"\bceasefire\b",
        r"\bcoast guard\b",
        r"\bconflict\b",
        r"\bdrone(s)?\b",
        r"\bmilitary exercise(s)?\b",
        r"\blive[- ]fire\b",
        r"\binvasion\b",
        r"\bmaritime patrol(s)?\b",
        r"\bmilitary\b",
        r"\bmissile(s)?\b",
        r"\bmobilization\b",
        r"\bnaval\b",
        r"\bpatrol(s)?\b",
        r"\bpla\b",
        r"\brocket(s)?\b",
        r"\btroop(s)?\b",
        r"\bwarship(s)?\b",
        r"\bweapon(s|ry)?\b",
        r"\bhimars\b",
        r"\bkinetic\b",
    )

    return any(re.search(pattern, normalized) for pattern in patterns)




DEESCALATION_PATTERNS = (
    r"\bceasefire\b",
    r"\bpeace talks?\b",
    r"\bde-escalat",
    r"\bwithdraw(s|al|ing)?\b",
    r"\btruce\b",
    r"\bstand[- ]down\b",
    r"\bconfidence-building\b",
)

ESCALATION_PATTERNS = (
    r"\battack(s|ed|ing)?\b",
    r"\bair\s*strike(s)?\b",
    r"\bmissile(s)?\b",
    r"\blive[- ]fire\b",
    r"\bmobilization\b",
    r"\bmilitary exercise(s)?\b",
    r"\bnaval patrol(s)?\b",
    r"\barmed clash(es)?\b",
    r"\bblockade\b",
    r"\binvasion\b",
    r"\bhimars\b",
)


def _infer_direction(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.lower()).strip()

    if any(
        re.search(pattern, normalized)
        for pattern in DEESCALATION_PATTERNS
    ):
        return "improving"

    if any(
        re.search(pattern, normalized)
        for pattern in ESCALATION_PATTERNS
    ):
        return "deteriorating"

    return "neutral"

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

    item_iso3 = str(item.get("country_iso3") or "").upper()
    if country_iso3 and item_iso3 == country_iso3.upper():
        return True

    return False


def _normalize_platform_signal(
    item: dict[str, Any],
    *,
    country_name: str | None,
    country_iso3: str | None,
    region: str | None,
) -> AgentSignal | None:
    title = str(item.get("title") or item.get("headline") or "").strip()
    summary = str(item.get("summary") or "").strip()
    domain = str(item.get("domain") or "").lower()
    drivers = item.get("drivers") or []

    combined_text = " ".join(
        [
            title,
            summary,
            domain,
            " ".join(str(driver) for driver in drivers),
        ]
    )

    domain_is_relevant = domain in {
        "conflict",
        "military",
        "security",
        "geopolitical",
        "chokepoint",
    }

    if not domain_is_relevant and not _contains_conflict_language(combined_text):
        return None

    if not _contains_conflict_language(combined_text):
        return None

    if not _country_matches(item, country_name, country_iso3):
        return None

    event_time = (
        item.get("published_at")
        or item.get("event_time")
        or item.get("created_at")
    )

    freshness = _freshness_factor(str(event_time or ""))

    raw_severity = _severity_to_score(
        item.get("signal_score") or item.get("severity"),
        fallback=45,
    )
    severity = round(raw_severity * freshness, 2)

    confidence = _severity_to_score(
        item.get("confidence"),
        fallback=65,
    )

    source = _extract_original_publisher(
        title,
        str(
            item.get("source")
            or item.get("provider")
            or "internal_signal_store"
        ),
    )

    reliability = _source_reliability(source)

    relevance = 88 if country_name or country_iso3 else 70
    materiality = round(
        severity * 0.50
        + confidence * 0.20
        + reliability * 0.20
        + relevance * 0.10,
        2,
    )

    return AgentSignal(
        signal_id=str(
            item.get("id")
            or item.get("signal_id")
            or f"live-{abs(hash(title))}"
        ),
        domain="conflict",
        signal_type=(
            "military_activity"
            if any(
                keyword in combined_text.lower()
                for keyword in (
                    "military",
                    "missile",
                    "naval",
                    "pla",
                    "forces",
                    "exercise",
                )
            )
            else "conflict_event"
        ),
        headline=title or "Conflict-related signal",
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
        entities=[],
        indicators=[
            {
                "name": "freshness_factor",
                "value": freshness,
            }
        ],
        tags=[domain] if domain else [],
    )


def _normalize_country_signal(
    item: dict[str, Any],
    *,
    country_name: str,
    country_iso3: str | None,
    region: str | None,
) -> AgentSignal | None:
    title = str(item.get("title") or "").strip()
    summary = str(item.get("summary") or "").strip()
    domain = str(item.get("signal_domain") or "").lower()
    combined_text = f"{title} {summary} {domain}"

    if not _contains_conflict_language(combined_text):
        return None

    event_time = item.get("published_at")
    freshness = _freshness_factor(str(event_time or ""))

    base_severity = _severity_to_score(
        item.get("severity"),
        fallback=35,
    )
    severity = round(base_severity * freshness, 2)

    source = _extract_original_publisher(
        title,
        str(item.get("source") or "country_intelligence"),
    )
    reliability = _source_reliability(source)
    confidence = round(55 + reliability * 0.25, 2)
    relevance = 92

    materiality = round(
        severity * 0.45
        + confidence * 0.20
        + reliability * 0.20
        + relevance * 0.15,
        2,
    )

    return AgentSignal(
        signal_id=f"country-{abs(hash(title))}",
        domain="conflict",
        signal_type=(
            "military_activity"
            if domain == "military"
            or any(
                word in combined_text.lower()
                for word in (
                    "military",
                    "missile",
                    "naval",
                    "pla",
                    "patrol",
                    "exercise",
                )
            )
            else "conflict_event"
        ),
        headline=title or "Country intelligence signal",
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
        entities=[],
        indicators=[
            {
                "name": "freshness_factor",
                "value": freshness,
            }
        ],
        tags=[domain] if domain else [],
    )


async def collect_live_conflict_signals(
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
            payload = response.json()

            for item in payload.get("signals", []):
                normalized = _normalize_platform_signal(
                    item,
                    country_name=country_name,
                    country_iso3=country_iso3,
                    region=region,
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
                payload = response.json()

                for item in payload.get("data", []):
                    normalized = _normalize_country_signal(
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

    return sorted(
        deduplicated.values(),
        key=lambda item: (
            item.materiality_score,
            item.severity,
            item.confidence,
        ),
        reverse=True,
    )[:limit]
