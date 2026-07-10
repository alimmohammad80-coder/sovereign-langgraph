from __future__ import annotations

import os
import re
from typing import Any


COUNTRY_ALIASES = {
    "Iran": ("iran", "iranian", "tehran"),
    "Pakistan": ("pakistan", "pakistani", "islamabad"),
    "Taiwan": ("taiwan", "taiwanese", "taipei"),
    "China": ("china", "chinese", "beijing"),
    "Russia": ("russia", "russian", "moscow"),
    "Ukraine": ("ukraine", "ukrainian", "kyiv", "kiev"),
}


def _matches_selected_country(
    text: str,
    country_name: str,
    country_iso3: str | None = None,
) -> bool:
    normalized = " ".join(
        str(text or "").lower().split()
    )

    aliases = COUNTRY_ALIASES.get(
        country_name,
        (country_name.lower(),),
    )

    for alias in aliases:
        pattern = (
            r"(?<![a-z0-9])"
            + re.escape(alias.lower())
            + r"(?![a-z0-9])"
        )

        if re.search(pattern, normalized):
            return True

    # Do not use raw ISO3 substring matching. Three-letter codes
    # can occur accidentally inside unrelated words or metadata.
    return False


import httpx

from app.agents.base_agent import AgentSignal
from app.services.worldbank_service import get_country_macro_snapshot


INTERNAL_API_BASE_URL = os.getenv(
    "STRATEGIC_INTERNAL_API_BASE_URL",
    "http://127.0.0.1:8000",
).rstrip("/")


ECONOMIC_PATTERNS = (
    r"\binflation\b",
    r"\bcurrency\b",
    r"\bdevaluation\b",
    r"\bdepreciation\b",
    r"\bsovereign debt\b",
    r"\bdefault\b",
    r"\bforeign reserves\b",
    r"\bcapital flight\b",
    r"\bbanking crisis\b",
    r"\bliquidity\b",
    r"\brecession\b",
    r"\bgdp\b",
    r"\bunemployment\b",
    r"\binterest rate\b",
    r"\bcentral bank\b",
    r"\bcurrent account\b",
    r"\bfiscal deficit\b",
    r"\bmarket stress\b",
)


def _risk_from_indicator(
    indicator_key: str,
    value: float,
    history: list[dict[str, Any]],
) -> tuple[float, str]:
    previous = (
        float(history[1]["value"])
        if len(history) > 1 and history[1].get("value") is not None
        else None
    )

    if indicator_key == "inflation_pct":
        if value >= 20:
            return 90, "deteriorating"
        if value >= 10:
            return 75, "deteriorating"
        if value >= 6:
            return 60, "deteriorating"
        if previous is not None and value < previous:
            return 30, "improving"
        return 35, "neutral"

    if indicator_key == "gdp_growth_pct":
        if value < -3:
            return 90, "deteriorating"
        if value < 0:
            return 75, "deteriorating"
        if value < 2:
            return 55, "deteriorating"
        if previous is not None and value > previous:
            return 28, "improving"
        return 35, "neutral"

    if indicator_key == "unemployment_pct":
        if value >= 15:
            return 85, "deteriorating"
        if value >= 10:
            return 70, "deteriorating"
        if value >= 7:
            return 55, "deteriorating"
        if previous is not None and value < previous:
            return 30, "improving"
        return 35, "neutral"

    if indicator_key == "current_account_pct_gdp":
        if value <= -8:
            return 85, "deteriorating"
        if value <= -5:
            return 70, "deteriorating"
        if value <= -3:
            return 55, "deteriorating"
        if value >= 0:
            return 25, "improving"
        return 35, "neutral"

    if indicator_key == "foreign_reserves_usd":
        if previous is not None and previous > 0:
            change_pct = ((value - previous) / previous) * 100
            if change_pct <= -25:
                return 85, "deteriorating"
            if change_pct <= -10:
                return 65, "deteriorating"
            if change_pct >= 20:
                return 25, "improving"
            if change_pct >= 5:
                return 32, "improving"
        return 40, "neutral"

    if indicator_key == "trade_pct_gdp":
        if previous is not None and value < previous - 5:
            return 60, "deteriorating"
        return 35, "neutral"

    if indicator_key == "gdp_current_usd":
        return 0, "neutral"

    return 40, "neutral"


def _macro_signals(
    snapshot: dict[str, Any],
    *,
    country_name: str,
    country_iso3: str,
    region: str | None,
) -> list[AgentSignal]:
    signals: list[AgentSignal] = []

    for indicator_key, payload in snapshot.get("indicators", {}).items():
        latest = payload.get("latest")
        history = payload.get("history") or []

        if not latest:
            continue

        value = float(latest["value"])
        severity, direction = _risk_from_indicator(
            indicator_key,
            value,
            history,
        )

        signals.append(
            AgentSignal(
                signal_id=(
                    f"worldbank-{country_iso3}-"
                    f"{indicator_key}-{latest['year']}"
                ),
                domain="economic",
                signal_type=indicator_key,
                headline=(
                    f"{country_name} {indicator_key.replace('_', ' ')} "
                    f"latest value: {value:.2f}"
                ),
                summary=(
                    f"World Bank latest observation for {country_name}: "
                    f"{indicator_key}={value:.2f} in {latest['year']}."
                ),
                country_iso3=country_iso3,
                country_name=country_name,
                region=region,
                severity=severity,
                relevance=95,
                confidence=92,
                source_reliability=95,
                materiality_score=round(
                    severity * 0.50
                    + 95 * 0.20
                    + 92 * 0.15
                    + 95 * 0.15,
                    2,
                ),
                direction=direction,
                event_time=f"{latest['year']}-12-31T00:00:00Z",
                source_key="World Bank",
                indicators=[
                    {
                        "name": indicator_key,
                        "value": value,
                        "year": latest["year"],
                    }
                ],
                tags=["macro", indicator_key],
            )
        )

    return signals


def _contains_economic_language(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.lower()).strip()
    return any(re.search(pattern, normalized) for pattern in ECONOMIC_PATTERNS)


async def collect_live_economic_signals(
    *,
    country_name: str,
    country_iso3: str,
    region: str | None = None,
    limit: int = 25,
) -> list[AgentSignal]:
    signals: list[AgentSignal] = []

    snapshot = await get_country_macro_snapshot(
        country_code=country_iso3,
    )
    signals.extend(
        _macro_signals(
            snapshot,
            country_name=country_name,
            country_iso3=country_iso3,
            region=region,
        )
    )

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            response = await client.get(
                f"{INTERNAL_API_BASE_URL}/api/financial-risk/live-signals"
            )
            response.raise_for_status()

            for item in response.json().get("signals", []):
                title = str(item.get("title") or "").strip()
                summary = str(item.get("summary") or "").strip()
                combined = f"{title} {summary}"

                if not _contains_economic_language(combined):
                    continue

                # This is a broad global financial-news feed. Require
                # country relevance in the headline or an explicit source
                # country field. An incidental country mention in the summary
                # is insufficient.
                item_country = str(
                    item.get("country")
                    or item.get("country_name")
                    or ""
                ).strip()

                headline_matches_country = _matches_selected_country(
                    title,
                    country_name,
                    country_iso3,
                )

                source_country_matches = bool(
                    item_country
                    and _matches_selected_country(
                        item_country,
                        country_name,
                        country_iso3,
                    )
                )

                if not (
                    headline_matches_country
                    or source_country_matches
                ):
                    continue

                signals.append(
                    AgentSignal(
                        signal_id=str(
                            item.get("id")
                            or f"financial-{abs(hash(title))}"
                        ),
                        domain="economic",
                        signal_type=str(
                            item.get("signal_type")
                            or "financial_risk_news"
                        ),
                        headline=title,
                        summary=summary or None,
                        country_iso3=country_iso3,
                        country_name=country_name,
                        region=region,
                        severity=float(
                            item.get("severity_score") or 45
                        ),
                        relevance=80,
                        confidence=float(
                            item.get("confidence_score") or 60
                        ),
                        source_reliability=65,
                        materiality_score=55,
                        direction="neutral",
                        event_time=item.get("published_at"),
                        source_key=item.get("source_name"),
                        evidence_url=item.get("source_url"),
                    )
                )
        except Exception:
            pass

        try:
            response = await client.get(
                f"{INTERNAL_API_BASE_URL}/api/country-intelligence/"
                f"debug/signals/{country_name}"
            )
            response.raise_for_status()

            for item in response.json().get("data", []):
                title = str(item.get("title") or "").strip()
                summary = str(item.get("summary") or "").strip()
                combined = (
                    f"{title} {summary} "
                    f"{item.get('signal_domain') or ''}"
                )

                if not _contains_economic_language(combined):
                    continue

                signals.append(
                    AgentSignal(
                        signal_id=f"country-economic-{abs(hash(title))}",
                        domain="economic",
                        signal_type="economic_news",
                        headline=title,
                        summary=summary or None,
                        country_iso3=country_iso3,
                        country_name=country_name,
                        region=region,
                        severity=40,
                        relevance=88,
                        confidence=68,
                        source_reliability=68,
                        materiality_score=54,
                        direction="neutral",
                        event_time=item.get("published_at"),
                        source_key=item.get("source"),
                        evidence_url=item.get("url"),
                    )
                )
        except Exception:
            pass

    deduplicated: dict[str, AgentSignal] = {}

    for signal in signals:
        key = re.sub(
            r"[^a-z0-9]+",
            " ",
            signal.headline.lower(),
        ).strip()

        current = deduplicated.get(key)

        if current is None or (
            signal.materiality_score > current.materiality_score
        ):
            deduplicated[key] = signal

    filtered = []

    for signal in deduplicated.values():
        # World Bank observations are already requested using
        # the selected country's ISO code and remain authoritative.
        if signal.source_key == "World Bank":
            filtered.append(signal)
            continue

        # Validate geographic relevance using only the original
        # evidence text. Assigned country metadata cannot prove relevance.
        combined = " ".join(
            str(value or "")
            for value in (
                signal.headline,
                signal.summary,
            )
        )

        if _matches_selected_country(
            combined,
            country_name,
            country_iso3,
        ):
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
