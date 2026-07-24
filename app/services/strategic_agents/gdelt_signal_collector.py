from __future__ import annotations

import asyncio
import hashlib
import time
from typing import Any

from app.agents.base_agent import AgentSignal
from app.services.gdelt_service import fetch_gdelt_news


GDELT_FAILURE_COOLDOWN_SECONDS = 60
_gdelt_unavailable_until = 0.0


def _gdelt_available() -> bool:
    return time.monotonic() >= _gdelt_unavailable_until


def _mark_gdelt_unavailable() -> None:
    global _gdelt_unavailable_until

    _gdelt_unavailable_until = (
        time.monotonic()
        + GDELT_FAILURE_COOLDOWN_SECONDS
    )


CONFLICT_TERMS = (
    "attack",
    "strike",
    "missile",
    "drone",
    "military",
    "troops",
    "conflict",
    "war",
    "clash",
    "violence",
    "protest",
    "unrest",
    "ceasefire",
    "escalation",
    "naval",
    "border",
)


def _signal_id(url: str | None, title: str) -> str:
    identity = f"{url or ''}|{title}".encode("utf-8")
    digest = hashlib.sha256(identity).hexdigest()[:24]
    return f"gdelt-{digest}"


def _severity(title: str) -> float:
    lowered = title.lower()

    high_terms = (
        "missile",
        "airstrike",
        "attack",
        "killed",
        "invasion",
        "bombing",
        "war",
    )
    medium_terms = (
        "military",
        "troops",
        "clash",
        "naval",
        "escalation",
        "ceasefire",
        "unrest",
    )

    if any(term in lowered for term in high_terms):
        return 72.0

    if any(term in lowered for term in medium_terms):
        return 58.0

    return 42.0


def _relevant(title: str) -> bool:
    lowered = title.lower()
    return any(term in lowered for term in CONFLICT_TERMS)


async def collect_gdelt_conflict_signals(
    *,
    country_name: str | None,
    country_iso3: str | None,
    region: str | None,
    limit: int = 5,
) -> list[AgentSignal]:
    if not country_name:
        return []

    if not _gdelt_available():
        print(
            "[GDELT Strategic Collector] "
            "Skipped during failure cooldown:",
            country_name,
        )
        return []

    query = (
        f'"{country_name}" '
        "(conflict OR military OR attack OR strike OR unrest "
        "OR protest OR escalation OR ceasefire)"
    )

    try:
        result: dict[str, Any] = await asyncio.to_thread(
            fetch_gdelt_news,
            query,
            max(1, min(limit * 2, 20)),
        )
    except Exception as exc:
        _mark_gdelt_unavailable()
        print(
            "[GDELT Strategic Collector] Request failed:",
            country_name,
            type(exc).__name__,
            str(exc),
        )
        return []

    if result.get("status") != "success":
        print(
            "[GDELT Strategic Collector] GDELT returned error:",
            result.get("message"),
        )
        return []

    signals: list[AgentSignal] = []
    seen: set[str] = set()

    for article in result.get("articles", []):
        title = str(
            article.get("title_en")
            or article.get("title")
            or ""
        ).strip()

        url = article.get("url")

        if not title or not _relevant(title):
            continue

        identity = str(url or title).strip().lower()

        if identity in seen:
            continue

        seen.add(identity)

        severity = _severity(title)

        signals.append(
            AgentSignal(
                signal_id=_signal_id(url, title),
                domain="conflict",
                signal_type="gdelt_conflict_news",
                headline=title,
                summary=article.get("summary_en")
                or article.get("summary"),
                country_iso3=country_iso3,
                country_name=country_name,
                region=region,
                severity=severity,
                relevance=78.0,
                confidence=62.0,
                source_reliability=65.0,
                materiality_score=severity * 0.85,
                direction="deteriorating",
                event_time=article.get("seendate"),
                source_key=(
                    article.get("domain")
                    or "GDELT"
                ),
                evidence_url=url,
                entities=[country_name],
                indicators=["gdelt_conflict_news"],
                tags=["gdelt", "conflict", "open_source"],
            )
        )

        if len(signals) >= limit:
            break

    print(
        "[GDELT Strategic Collector] Collected:",
        len(signals),
        country_name,
    )

    return signals


POLITICAL_TERMS = (
    "protest",
    "demonstration",
    "election",
    "government",
    "parliament",
    "president",
    "minister",
    "resignation",
    "coup",
    "unrest",
    "opposition",
    "crackdown",
    "arrest",
    "corruption",
    "leadership",
    "regime",
)


def _political_relevant(title: str) -> bool:
    lowered = title.lower()
    return any(term in lowered for term in POLITICAL_TERMS)


def _political_severity(title: str) -> float:
    lowered = title.lower()

    high_terms = (
        "coup",
        "government collapse",
        "mass protest",
        "crackdown",
        "assassination",
        "state of emergency",
    )

    medium_terms = (
        "protest",
        "unrest",
        "resignation",
        "election violence",
        "opposition",
        "arrest",
    )

    if any(term in lowered for term in high_terms):
        return 74.0

    if any(term in lowered for term in medium_terms):
        return 58.0

    return 42.0


async def collect_gdelt_political_signals(
    *,
    country_name: str | None,
    country_iso3: str | None,
    region: str | None,
    limit: int = 5,
) -> list[AgentSignal]:
    if not country_name:
        return []

    if not _gdelt_available():
        print(
            "[GDELT Political Collector] "
            "Skipped during failure cooldown:",
            country_name,
        )
        return []

    query = (
        f'"{country_name}" '
        "(protest OR election OR government OR opposition "
        "OR unrest OR coup OR resignation OR crackdown)"
    )

    try:
        result: dict[str, Any] = await asyncio.to_thread(
            fetch_gdelt_news,
            query,
            max(1, min(limit * 2, 20)),
        )
    except Exception as exc:
        _mark_gdelt_unavailable()
        print(
            "[GDELT Political Collector] Request failed:",
            country_name,
            type(exc).__name__,
            str(exc),
        )
        return []

    if result.get("status") != "success":
        print(
            "[GDELT Political Collector] GDELT returned error:",
            result.get("message"),
        )
        return []

    signals: list[AgentSignal] = []
    seen: set[str] = set()

    for article in result.get("articles", []):
        title = str(
            article.get("title_en")
            or article.get("title")
            or ""
        ).strip()

        url = article.get("url")

        if not title or not _political_relevant(title):
            continue

        identity = str(url or title).strip().lower()

        if identity in seen:
            continue

        seen.add(identity)
        severity = _political_severity(title)

        signals.append(
            AgentSignal(
                signal_id=_signal_id(url, title),
                domain="political",
                signal_type="gdelt_political_news",
                headline=title,
                summary=article.get("summary_en")
                or article.get("summary"),
                country_iso3=country_iso3,
                country_name=country_name,
                region=region,
                severity=severity,
                relevance=76.0,
                confidence=62.0,
                source_reliability=65.0,
                materiality_score=severity * 0.85,
                direction="deteriorating",
                event_time=article.get("seendate"),
                source_key=article.get("domain") or "GDELT",
                evidence_url=url,
                entities=[country_name],
                indicators=["gdelt_political_news"],
                tags=["gdelt", "political", "open_source"],
            )
        )

        if len(signals) >= limit:
            break

    print(
        "[GDELT Political Collector] Collected:",
        len(signals),
        country_name,
    )

    return signals
