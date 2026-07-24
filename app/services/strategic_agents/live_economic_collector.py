from __future__ import annotations

import asyncio
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
from app.services.fred_service import get_fred_market_snapshot
from app.services.eia_service import get_eia_energy_snapshot
from app.services.imf_service import get_imf_country_snapshot
from app.services.un_comtrade_service import (
    get_comtrade_country_snapshot,
)


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


def _fred_context_signals(
    snapshot: dict[str, Any],
    *,
    country_name: str,
    country_iso3: str,
    region: str | None,
) -> list[AgentSignal]:
    signals: list[AgentSignal] = []

    for series_key, payload in (
        snapshot.get("series") or {}
    ).items():
        observations = payload.get("observations") or []

        if payload.get("status") != "success":
            continue

        if not observations:
            continue

        latest = observations[0]
        previous = (
            observations[1]
            if len(observations) > 1
            else None
        )

        value = float(latest["value"])
        prior_value = (
            float(previous["value"])
            if previous
            else None
        )

        severity = 30.0
        direction = "neutral"

        if series_key == "vix_index":
            if value >= 40:
                severity = 85.0
                direction = "deteriorating"
            elif value >= 30:
                severity = 70.0
                direction = "deteriorating"
            elif value >= 22:
                severity = 55.0
                direction = "deteriorating"
            else:
                severity = 25.0

        elif series_key in {
            "wti_crude_usd",
            "brent_crude_usd",
        }:
            if prior_value and prior_value > 0:
                change_pct = (
                    (value - prior_value)
                    / prior_value
                    * 100
                )

                if abs(change_pct) >= 8:
                    severity = 65.0
                    direction = (
                        "deteriorating"
                        if change_pct > 0
                        else "improving"
                    )
                elif abs(change_pct) >= 4:
                    severity = 50.0
                    direction = (
                        "deteriorating"
                        if change_pct > 0
                        else "improving"
                    )

        elif series_key == "broad_usd_index":
            if prior_value and prior_value > 0:
                change_pct = (
                    (value - prior_value)
                    / prior_value
                    * 100
                )

                if change_pct >= 2:
                    severity = 55.0
                    direction = "deteriorating"
                elif change_pct <= -2:
                    severity = 30.0
                    direction = "improving"

        elif series_key == "federal_funds_rate":
            if value >= 6:
                severity = 60.0
                direction = "deteriorating"
            elif value >= 4:
                severity = 45.0
                direction = "neutral"
            else:
                severity = 30.0

        signals.append(
            AgentSignal(
                signal_id=(
                    f"fred-{series_key}-"
                    f"{latest['date']}"
                ),
                domain="economic",
                signal_type=f"fred_{series_key}",
                headline=(
                    f"FRED {series_key.replace('_', ' ')} "
                    f"latest value: {value:.2f}"
                ),
                summary=(
                    f"Global market-context indicator from FRED. "
                    f"Latest observation {value:.2f} on "
                    f"{latest['date']}."
                ),
                country_iso3=country_iso3,
                country_name=country_name,
                region=region,
                severity=severity,
                relevance=55.0,
                confidence=90.0,
                source_reliability=95.0,
                materiality_score=round(
                    severity * 0.35
                    + 55 * 0.20
                    + 90 * 0.20
                    + 95 * 0.25,
                    2,
                ),
                direction=direction,
                event_time=f"{latest['date']}T00:00:00Z",
                observation_date=(
                    f"{latest['date']}T00:00:00Z"
                ),
                source_key="FRED",
                source_category=f"fred_{series_key}",
                freshness_type="recent",
                is_structural=False,
                is_live=False,
                indicators=[
                    {
                        "name": series_key,
                        "value": value,
                        "date": latest["date"],
                    }
                ],
                tags=[
                    "macro",
                    "market_context",
                    "fred",
                    series_key,
                ],
            )
        )

    return signals


def _eia_context_signals(
    snapshot: dict[str, Any],
    *,
    country_name: str,
    country_iso3: str,
    region: str | None,
) -> list[AgentSignal]:
    signals: list[AgentSignal] = []

    # WTI and Brent are intentionally excluded here because FRED
    # already supplies those price series to the agent. Including
    # them again would double-count the same market movement.
    included_series = {
        "commercial_crude_stocks",
        "us_crude_production",
    }

    for series_key, payload in (
        snapshot.get("series") or {}
    ).items():
        if series_key not in included_series:
            continue

        observations = payload.get("observations") or []

        if payload.get("status") != "success":
            continue

        if not observations:
            continue

        latest = observations[0]
        previous = (
            observations[1]
            if len(observations) > 1
            else None
        )

        value = float(latest["value"])
        previous_value = (
            float(previous["value"])
            if previous
            else None
        )

        change_pct = 0.0

        if previous_value and previous_value > 0:
            change_pct = (
                (value - previous_value)
                / previous_value
                * 100
            )

        severity = 25.0
        direction = "neutral"

        if series_key == "commercial_crude_stocks":
            # Rapid inventory drawdowns may indicate tightening supply.
            if change_pct <= -5:
                severity = 65.0
                direction = "deteriorating"
            elif change_pct <= -2:
                severity = 50.0
                direction = "deteriorating"
            elif change_pct >= 5:
                severity = 25.0
                direction = "improving"
            elif change_pct >= 2:
                severity = 30.0
                direction = "improving"

        elif series_key == "us_crude_production":
            # Material production declines may tighten global supply.
            if change_pct <= -3:
                severity = 60.0
                direction = "deteriorating"
            elif change_pct <= -1:
                severity = 45.0
                direction = "deteriorating"
            elif change_pct >= 3:
                severity = 25.0
                direction = "improving"
            elif change_pct >= 1:
                severity = 30.0
                direction = "improving"

        description = (
            latest.get("description")
            or series_key.replace("_", " ")
        )

        units = latest.get("units") or ""

        signals.append(
            AgentSignal(
                signal_id=(
                    f"eia-{series_key}-"
                    f"{latest['date']}"
                ),
                domain="economic",
                signal_type=f"eia_{series_key}",
                headline=(
                    f"EIA {series_key.replace('_', ' ')} "
                    f"latest value: {value:,.2f} {units}"
                ).strip(),
                summary=(
                    f"{description}. Latest observation was "
                    f"{value:,.2f} {units} on {latest['date']}. "
                    f"Change from the preceding observation: "
                    f"{change_pct:+.2f}%."
                ),
                country_iso3=country_iso3,
                country_name=country_name,
                region=region,
                severity=severity,
                relevance=45.0,
                confidence=92.0,
                source_reliability=97.0,
                materiality_score=round(
                    severity * 0.35
                    + 45 * 0.20
                    + 92 * 0.20
                    + 97 * 0.25,
                    2,
                ),
                direction=direction,
                event_time=f"{latest['date']}T00:00:00Z",
                observation_date=(
                    f"{latest['date']}T00:00:00Z"
                ),
                source_key="EIA",
                source_category=f"eia_{series_key}",
                freshness_type="recent",
                is_structural=False,
                is_live=False,
                indicators=[
                    {
                        "name": series_key,
                        "value": value,
                        "units": units,
                        "date": latest["date"],
                        "change_pct": round(change_pct, 2),
                    }
                ],
                tags=[
                    "energy",
                    "market_context",
                    "eia",
                    series_key,
                ],
            )
        )

    return signals


def _imf_country_signals(
    snapshot: dict[str, Any],
    *,
    country_name: str,
    country_iso3: str,
    region: str | None,
) -> list[AgentSignal]:
    signals: list[AgentSignal] = []

    included_series = {
        "government_debt_pct_gdp",
        "fiscal_balance_pct_gdp",
        "current_account_pct_gdp",
    }

    for indicator_key, payload in (
        snapshot.get("series") or {}
    ).items():
        if indicator_key not in included_series:
            continue

        if payload.get("status") != "success":
            continue

        observations = payload.get("observations") or []

        estimate = next(
            (
                row
                for row in observations
                if row.get("status") == "estimate"
            ),
            None,
        )

        historical = next(
            (
                row
                for row in observations
                if row.get("status") == "historical"
            ),
            None,
        )

        forecast = next(
            (
                row
                for row in sorted(
                    observations,
                    key=lambda item: item["year"],
                )
                if row.get("status") == "forecast"
            ),
            None,
        )

        latest = estimate or historical

        if not latest:
            continue

        value = float(latest["value"])
        year = int(latest["year"])

        previous_value = (
            float(historical["value"])
            if historical
            else None
        )

        forecast_value = (
            float(forecast["value"])
            if forecast
            else None
        )

        severity = 30.0
        direction = "neutral"

        if indicator_key == "government_debt_pct_gdp":
            if value >= 100:
                severity = 80.0
                direction = "deteriorating"
            elif value >= 70:
                severity = 65.0
                direction = "deteriorating"
            elif value >= 50:
                severity = 50.0
                direction = "deteriorating"
            elif (
                previous_value is not None
                and value - previous_value >= 5
            ):
                severity = 45.0
                direction = "deteriorating"
            else:
                severity = 30.0

        elif indicator_key == "fiscal_balance_pct_gdp":
            if value <= -10:
                severity = 80.0
                direction = "deteriorating"
            elif value <= -7:
                severity = 65.0
                direction = "deteriorating"
            elif value <= -4:
                severity = 55.0
                direction = "deteriorating"
            elif value < 0:
                severity = 40.0
                direction = "deteriorating"
            else:
                severity = 25.0
                direction = "improving"

        elif indicator_key == "current_account_pct_gdp":
            if value <= -10:
                severity = 75.0
                direction = "deteriorating"
            elif value <= -5:
                severity = 60.0
                direction = "deteriorating"
            elif value < 0:
                severity = 45.0
                direction = "deteriorating"
            elif value >= 5:
                severity = 20.0
                direction = "improving"
            else:
                severity = 30.0
                direction = "neutral"

        forecast_text = ""

        if forecast is not None:
            forecast_text = (
                f" IMF forecast for {forecast['year']}: "
                f"{forecast_value:.2f}%."
            )

        signals.append(
            AgentSignal(
                signal_id=(
                    f"imf-{country_iso3}-"
                    f"{indicator_key}-{year}"
                ),
                domain="economic",
                signal_type=f"imf_{indicator_key}",
                headline=(
                    f"{country_name} IMF "
                    f"{indicator_key.replace('_', ' ')} "
                    f"estimate: {value:.2f}%"
                ),
                summary=(
                    f"IMF {latest['status']} for {country_name}: "
                    f"{indicator_key} was {value:.2f}% in {year}."
                    f"{forecast_text}"
                ),
                country_iso3=country_iso3,
                country_name=country_name,
                region=region,
                severity=severity,
                relevance=92.0,
                confidence=90.0,
                source_reliability=95.0,
                materiality_score=round(
                    severity * 0.45
                    + 92 * 0.20
                    + 90 * 0.15
                    + 95 * 0.20,
                    2,
                ),
                direction=direction,
                event_time=f"{year}-01-01T00:00:00Z",
                observation_date=f"{year}-01-01T00:00:00Z",
                source_key="IMF",
                source_category=f"imf_{indicator_key}",
                freshness_type="structural",
                is_structural=True,
                is_live=False,
                indicators=[
                    {
                        "name": indicator_key,
                        "value": value,
                        "year": year,
                        "value_status": latest["status"],
                        "next_forecast_year": (
                            forecast.get("year")
                            if forecast
                            else None
                        ),
                        "next_forecast_value": forecast_value,
                    }
                ],
                tags=[
                    "macro",
                    "sovereign_finance",
                    "imf",
                    indicator_key,
                ],
            )
        )

    return signals


def _comtrade_country_signals(
    snapshot: dict[str, Any],
    *,
    country_name: str,
    country_iso3: str,
    region: str | None,
) -> list[AgentSignal]:
    signals: list[AgentSignal] = []

    export_result = snapshot.get("exports") or {}
    import_result = snapshot.get("imports") or {}

    export_observation = export_result.get("observation")
    import_observation = import_result.get("observation")

    if (
        export_result.get("status") != "success"
        or import_result.get("status") != "success"
        or not export_observation
        or not import_observation
    ):
        return signals

    exports_usd = float(export_observation["value_usd"])
    imports_usd = float(import_observation["value_usd"])

    export_year = int(export_observation["year"])
    import_year = int(import_observation["year"])

    observation_year = min(export_year, import_year)
    trade_balance_usd = exports_usd - imports_usd

    total_trade_usd = exports_usd + imports_usd

    import_share = (
        imports_usd / total_trade_usd * 100
        if total_trade_usd > 0
        else 0.0
    )

    balance_ratio = (
        trade_balance_usd / total_trade_usd * 100
        if total_trade_usd > 0
        else 0.0
    )

    export_severity = 25.0
    export_direction = "neutral"

    if exports_usd < 10_000_000_000:
        export_severity = 50.0
        export_direction = "deteriorating"
    elif exports_usd < 30_000_000_000:
        export_severity = 40.0
        export_direction = "neutral"

    import_severity = 30.0
    import_direction = "neutral"

    if import_share >= 65:
        import_severity = 60.0
        import_direction = "deteriorating"
    elif import_share >= 55:
        import_severity = 45.0
        import_direction = "deteriorating"

    balance_severity = 25.0
    balance_direction = "neutral"

    if balance_ratio <= -20:
        balance_severity = 65.0
        balance_direction = "deteriorating"
    elif balance_ratio < 0:
        balance_severity = 50.0
        balance_direction = "deteriorating"
    elif balance_ratio >= 20:
        balance_severity = 20.0
        balance_direction = "improving"

    common_fields = {
        "domain": "economic",
        "country_iso3": country_iso3,
        "country_name": country_name,
        "region": region,
        "confidence": 88.0,
        "source_reliability": 92.0,
        "event_time": f"{observation_year}-12-31T00:00:00Z",
        "observation_date": (
            f"{observation_year}-12-31T00:00:00Z"
        ),
        "source_key": "UN Comtrade",
        "freshness_type": "structural",
        "is_structural": True,
        "is_live": False,
        "tags": [
            "trade",
            "structural",
            "un_comtrade",
        ],
    }

    signals.append(
        AgentSignal(
            signal_id=(
                f"comtrade-{country_iso3}-"
                f"exports-{observation_year}"
            ),
            signal_type="comtrade_total_exports",
            headline=(
                f"{country_name} total merchandise exports: "
                f"${exports_usd / 1_000_000_000:.2f}B"
            ),
            summary=(
                f"UN Comtrade reports total merchandise exports "
                f"of ${exports_usd:,.0f} in {observation_year}."
            ),
            severity=export_severity,
            relevance=78.0,
            materiality_score=round(
                export_severity * 0.40
                + 78 * 0.20
                + 88 * 0.15
                + 92 * 0.25,
                2,
            ),
            direction=export_direction,
            source_category="comtrade_total_exports",
            indicators=[
                {
                    "name": "total_exports_usd",
                    "value": exports_usd,
                    "year": observation_year,
                }
            ],
            **common_fields,
        )
    )

    signals.append(
        AgentSignal(
            signal_id=(
                f"comtrade-{country_iso3}-"
                f"imports-{observation_year}"
            ),
            signal_type="comtrade_import_share",
            headline=(
                f"{country_name} imports represent "
                f"{import_share:.1f}% of total merchandise trade"
            ),
            summary=(
                f"UN Comtrade reports imports of "
                f"${imports_usd:,.0f} in {observation_year}. "
                f"Imports represented {import_share:.1f}% of "
                f"combined merchandise trade."
            ),
            severity=import_severity,
            relevance=82.0,
            materiality_score=round(
                import_severity * 0.40
                + 82 * 0.20
                + 88 * 0.15
                + 92 * 0.25,
                2,
            ),
            direction=import_direction,
            source_category="comtrade_import_share",
            indicators=[
                {
                    "name": "imports_usd",
                    "value": imports_usd,
                    "year": observation_year,
                },
                {
                    "name": "import_share_total_trade_pct",
                    "value": round(import_share, 2),
                },
            ],
            **common_fields,
        )
    )

    signals.append(
        AgentSignal(
            signal_id=(
                f"comtrade-{country_iso3}-"
                f"trade-balance-{observation_year}"
            ),
            signal_type="comtrade_trade_balance",
            headline=(
                f"{country_name} merchandise trade balance: "
                f"${trade_balance_usd / 1_000_000_000:.2f}B"
            ),
            summary=(
                f"Exports exceeded imports by "
                f"${trade_balance_usd:,.0f} in {observation_year}. "
                f"The balance equalled {balance_ratio:.1f}% of "
                f"total merchandise trade."
            ),
            severity=balance_severity,
            relevance=88.0,
            materiality_score=round(
                balance_severity * 0.40
                + 88 * 0.20
                + 88 * 0.15
                + 92 * 0.25,
                2,
            ),
            direction=balance_direction,
            source_category="comtrade_trade_balance",
            indicators=[
                {
                    "name": "trade_balance_usd",
                    "value": trade_balance_usd,
                    "year": observation_year,
                },
                {
                    "name": "trade_balance_ratio_pct",
                    "value": round(balance_ratio, 2),
                },
            ],
            **common_fields,
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

    (
        snapshot,
        fred_snapshot,
        eia_snapshot,
        imf_snapshot,
        comtrade_snapshot,
    ) = await asyncio.gather(
        get_country_macro_snapshot(
            country_code=country_iso3,
        ),
        get_fred_market_snapshot(),
        get_eia_energy_snapshot(),
        get_imf_country_snapshot(
            country_iso3,
        ),
        get_comtrade_country_snapshot(
            country_iso3,
        ),
    )

    signals.extend(
        _macro_signals(
            snapshot,
            country_name=country_name,
            country_iso3=country_iso3,
            region=region,
        )
    )

    signals.extend(
        _fred_context_signals(
            fred_snapshot,
            country_name=country_name,
            country_iso3=country_iso3,
            region=region,
        )
    )

    signals.extend(
        _eia_context_signals(
            eia_snapshot,
            country_name=country_name,
            country_iso3=country_iso3,
            region=region,
        )
    )

    signals.extend(
        _imf_country_signals(
            imf_snapshot,
            country_name=country_name,
            country_iso3=country_iso3,
            region=region,
        )
    )

    signals.extend(
        _comtrade_country_signals(
            comtrade_snapshot,
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
        if signal.source_key in {
            "World Bank",
            "FRED",
            "EIA",
            "IMF",
            "UN Comtrade",
        }:
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
