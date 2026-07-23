from __future__ import annotations

import hashlib
import os
import re
from typing import Any

import httpx

from app.agents.base_agent import AgentSignal


INTERNAL_API_BASE_URL = os.getenv(
    "STRATEGIC_INTERNAL_API_BASE_URL",
    "http://127.0.0.1:8000",
).rstrip("/")


ENERGY_COMMODITIES = {
    "oil",
    "lng",
    "natural gas",
    "gas",
    "refined petroleum",
    "diesel",
    "gasoline",
    "jet fuel",
    "propane",
    "heating oil",
    "crude",
}


ENERGY_TERMS = (
    r"\boil\b",
    r"\blng\b",
    r"\bnatural gas\b",
    r"\bgas pipeline\b",
    r"\brefinery\b",
    r"\bpetroleum\b",
    r"\bcrude\b",
    r"\benergy infrastructure\b",
    r"\btanker\b",
    r"\bpipeline\b",
    r"\bterminal\b",
    r"\bpower grid\b",
    r"\belectricity\b",
    r"\bblackout\b",
    r"\benergy supply\b",
    r"\benergy security\b",
)


ENERGY_SANCTIONS_TERMS = (
    "oil",
    "gas",
    "lng",
    "petroleum",
    "tanker",
    "shipping",
    "energy",
    "pipeline",
    "refinery",
)


CONFIDENCE_MAP = {
    "high": 88,
    "medium-high": 80,
    "medium": 68,
    "low-medium": 55,
    "low": 45,
}


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}-{digest}"


def _numeric_confidence(value: Any, fallback: float = 65) -> float:
    if isinstance(value, (int, float)):
        numeric = float(value)
        if numeric <= 10:
            return max(0, min(100, numeric * 10))
        return max(0, min(100, numeric))

    normalized = str(value or "").strip().lower()

    if normalized in CONFIDENCE_MAP:
        return float(CONFIDENCE_MAP[normalized])

    return fallback


def _contains_energy_language(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.lower()).strip()
    return any(re.search(pattern, normalized) for pattern in ENERGY_TERMS)


def _country_matches(
    countries: list[str],
    country_name: str | None,
) -> bool:
    if not country_name:
        return True

    normalized = country_name.strip().lower()
    return any(str(country).strip().lower() == normalized for country in countries)


REGIONAL_ENERGY_RELEVANCE: dict[str, set[str]] = {
    "middle east": {
        "hormuz",
        "bab-el-mandeb",
        "suez",
        "port-jebel-ali",
    },
    "europe": {
        "bosporus",
        "gibraltar",
        "port-rotterdam",
        "suez",
    },
    "east asia": {
        "taiwan-strait",
        "port-shanghai",
        "port-busan",
    },
    "southeast asia": {
        "malacca",
        "port-singapore",
    },
    "north america": {
        "port-la-longbeach",
        "port-houston",
        "panama-canal",
    },
    "south asia": {
        "port-colombo",
        "malacca",
    },
    "eurasia": {
        "bosporus",
    },
    "central asia": set(),
    "sub-saharan africa": {
        "bab-el-mandeb",
    },
    "latin america and caribbean": {
        "panama-canal",
    },
}


def _region_matches_chokepoint(
    row: dict[str, Any],
    region: str | None,
) -> bool:
    if not region:
        return True

    allowed = REGIONAL_ENERGY_RELEVANCE.get(
        region.strip().lower()
    )

    if allowed is None:
        return False

    row_id = str(row.get("id") or "").strip().lower()

    return row_id in allowed


def _marine_weather_relevant(
    payload: dict[str, Any],
    region: str | None,
) -> bool:
    if not region:
        return True

    location = str(
        (payload.get("data") or {}).get("location_name")
        or ""
    ).strip().lower()

    normalized_region = region.strip().lower()

    if "hormuz" in location:
        return normalized_region == "middle east"

    return True


def _chokepoint_signals(
    rows: list[dict[str, Any]],
    *,
    country_name: str | None,
    country_iso3: str | None,
    region: str | None,
) -> list[AgentSignal]:
    signals: list[AgentSignal] = []

    for row in rows:
        commodities = [
            str(item)
            for item in row.get("affected_commodities", [])
        ]
        sectors = [
            str(item)
            for item in row.get("affected_sectors", [])
        ]
        countries = [
            str(item)
            for item in row.get("countries", [])
        ]

        energy_relevant = (
            any(item.lower() in ENERGY_COMMODITIES for item in commodities)
            or any(item.lower() == "energy" for item in sectors)
        )

        if not energy_relevant:
            continue

        # Regional assessments treat strategic infrastructure as
        # region-level evidence. A chokepoint does not need to be
        # physically located inside one of the region's countries if
        # it is explicitly mapped as strategically relevant.
        if region:
            if not _region_matches_chokepoint(
                row,
                region,
            ):
                continue
        elif not _country_matches(
            countries,
            country_name,
        ):
            continue

        score = float(row.get("risk_score") or 0)
        confidence = _numeric_confidence(row.get("confidence"), 68)

        drivers = [
            str(item)
            for item in row.get("primary_drivers", [])
        ]

        headline = (
            f"{row.get('name', 'Energy chokepoint')} energy exposure "
            f"rated {row.get('risk_level', 'Unknown')} at {score:.1f}"
        )

        signals.append(
            AgentSignal(
                signal_id=f"energy-chokepoint-{row.get('id')}",
                domain="energy",
                signal_type="energy_chokepoint_risk",
                headline=headline,
                summary=(
                    f"Affected commodities: {', '.join(commodities)}. "
                    f"Primary drivers: {', '.join(drivers)}."
                ),
                country_iso3=(
                    None if region else country_iso3
                ),
                country_name=(
                    None if region else country_name
                ),
                region=(
                    region
                    if region
                    else str(row.get("region") or "")
                ),
                severity=score,
                relevance=95,
                confidence=confidence,
                source_reliability=82,
                materiality_score=round(
                    score * 0.55
                    + confidence * 0.20
                    + 95 * 0.15
                    + 82 * 0.10,
                    2,
                ),
                # A high structural chokepoint score does not by itself
                # prove that conditions are currently deteriorating.
                direction="neutral",
                source_key="Sovereign Supply Chain Risk Engine",
                is_structural=True,
                freshness_type="structural",
                indicators=[
                    {
                        "name": "chokepoint_risk_score",
                        "value": score,
                    },
                    {
                        "name": "affected_commodities",
                        "value": commodities,
                    },
                ],
                tags=["energy", "chokepoint"],
            )
        )

    return signals


def _marine_weather_signal(
    payload: dict[str, Any],
    *,
    country_name: str | None,
    country_iso3: str | None,
    region: str | None,
) -> AgentSignal | None:
    data = payload.get("data") or {}

    if not data:
        return None

    severity = float(data.get("severity_score") or 0)
    reliability = _numeric_confidence(
        data.get("reliability_score"),
        70,
    )
    location = str(data.get("location_name") or "Marine route")

    return AgentSignal(
        signal_id=_stable_id(
            "energy-weather",
            f"{location}-{data.get('max_wave_height_m')}",
        ),
        domain="energy",
        signal_type="marine_weather_disruption",
        headline=(
            f"{location} marine weather severity "
            f"{data.get('severity', 'Unknown')}"
        ),
        summary=str(data.get("summary") or ""),
        country_iso3=country_iso3,
        country_name=country_name,
        region=region,
        severity=severity,
        relevance=80,
        confidence=reliability,
        source_reliability=78,
        materiality_score=round(
            severity * 0.55
            + reliability * 0.20
            + 80 * 0.15
            + 78 * 0.10,
            2,
        ),
        direction=(
            "deteriorating"
            if severity >= 50
            else "neutral"
        ),
        source_key="Open-Meteo Marine Weather",
        indicators=[
            {
                "name": "max_wave_height_m",
                "value": data.get("max_wave_height_m"),
            }
        ],
        tags=["energy", "weather", "maritime"],
    )


def _eia_signal(
    payload: dict[str, Any],
    *,
    country_name: str | None,
    country_iso3: str | None,
    region: str | None,
) -> AgentSignal | None:
    eia = (
        payload.get("data", {})
        .get("eia_signals", {})
    )

    if not isinstance(eia, dict):
        return None

    rows = (
        eia.get("data", {})
        .get("response", {})
        .get("data", [])
    )

    if not rows:
        return None

    energy_rows = []

    for row in rows[:100]:
        text = " ".join(
            str(row.get(field) or "")
            for field in (
                "product-name",
                "series-description",
                "units",
            )
        )

        if _contains_energy_language(text):
            energy_rows.append(row)

    if not energy_rows:
        return None

    # EIA observations provide market context. The upstream
    # severity field is not a 0-100 geopolitical risk score.
    severity = 0.0

    reliability_raw = float(eia.get("reliability_score") or 0)
    reliability = (
        reliability_raw * 10
        if reliability_raw <= 10
        else reliability_raw
    )

    sample = energy_rows[:8]

    return AgentSignal(
        signal_id=_stable_id(
            "energy-eia",
            "|".join(str(row.get("series") or "") for row in sample),
        ),
        domain="energy",
        signal_type="energy_market_signal",
        headline="EIA petroleum and energy market observations available",
        summary=(
            f"{len(energy_rows)} recent energy-price observations "
            f"were returned by the EIA feed."
        ),
        country_iso3=country_iso3,
        country_name=country_name,
        region=region,
        severity=severity,
        relevance=72,
        confidence=reliability,
        source_reliability=95,
        materiality_score=round(
            severity * 0.45
            + reliability * 0.20
            + 72 * 0.15
            + 95 * 0.20,
            2,
        ),
        direction="neutral",
        source_key="U.S. Energy Information Administration",
        indicators=[
            {
                "name": str(row.get("series-description") or row.get("product-name")),
                "value": row.get("value"),
                "units": row.get("units"),
                "period": row.get("period"),
            }
            for row in sample
        ],
        tags=["energy", "market", "eia"],
    )


def _ofac_signals(
    payload: dict[str, Any],
    *,
    country_name: str | None,
    country_iso3: str | None,
    region: str | None,
) -> list[AgentSignal]:
    rows = (
        payload.get("data", {})
        .get("ofac_signals", [])
    )

    signals: list[AgentSignal] = []

    for row in rows:
        text = " ".join(
            str(row.get(field) or "")
            for field in (
                "name",
                "program",
                "summary",
                "signal_type",
            )
        ).lower()

        if not any(term in text for term in ENERGY_SANCTIONS_TERMS):
            continue

        severity_raw = float(row.get("severity_score") or 0)
        severity = severity_raw * 10 if severity_raw <= 10 else severity_raw

        reliability_raw = float(row.get("reliability_score") or 0)
        reliability = (
            reliability_raw * 10
            if reliability_raw <= 10
            else reliability_raw
        )

        name = str(row.get("name") or "Energy sanctions entity")

        signals.append(
            AgentSignal(
                signal_id=_stable_id("energy-ofac", name),
                domain="energy",
                signal_type="energy_sanctions_exposure",
                headline=f"Energy-linked sanctions exposure: {name}",
                summary=str(row.get("summary") or ""),
                country_iso3=country_iso3,
                country_name=country_name,
                region=region,
                severity=severity,
                relevance=78,
                confidence=reliability,
                source_reliability=98,
                materiality_score=round(
                    severity * 0.45
                    + reliability * 0.20
                    + 78 * 0.15
                    + 98 * 0.20,
                    2,
                ),
                direction="deteriorating",
                source_key="OFAC",
                tags=["energy", "sanctions"],
            )
        )

    return signals


async def collect_live_energy_signals(
    *,
    country_name: str | None = None,
    country_iso3: str | None = None,
    region: str | None = None,
    limit: int = 25,
) -> list[AgentSignal]:
    signals: list[AgentSignal] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        chokepoint_payload: dict[str, Any] = {}
        live_payload: dict[str, Any] = {}
        marine_payload: dict[str, Any] = {}

        try:
            response = await client.get(
                f"{INTERNAL_API_BASE_URL}/api/supply-chain/chokepoints"
            )
            response.raise_for_status()
            chokepoint_payload = response.json()
        except Exception:
            pass

        try:
            response = await client.get(
                f"{INTERNAL_API_BASE_URL}/api/supply-chain/live-signals"
            )
            response.raise_for_status()
            live_payload = response.json()
        except Exception:
            pass

        try:
            response = await client.get(
                f"{INTERNAL_API_BASE_URL}/api/supply-chain/"
                "external/marine-weather"
            )
            response.raise_for_status()
            marine_payload = response.json()
        except Exception:
            pass

    signals.extend(
        _chokepoint_signals(
            chokepoint_payload.get("data", []),
            country_name=country_name,
            country_iso3=country_iso3,
            region=region,
        )
    )

    weather = None

    if _marine_weather_relevant(
        marine_payload,
        region,
    ):
        weather = _marine_weather_signal(
            marine_payload,
            country_name=country_name,
            country_iso3=country_iso3,
            region=region,
        )

    if weather:
        signals.append(weather)

    eia = _eia_signal(
        live_payload,
        country_name=country_name,
        country_iso3=country_iso3,
        region=region,
    )
    if eia:
        signals.append(eia)

    signals.extend(
        _ofac_signals(
            live_payload,
            country_name=country_name,
            country_iso3=country_iso3,
            region=region,
        )
    )

    deduplicated: dict[str, AgentSignal] = {}

    for signal in signals:
        key = signal.signal_id
        current = deduplicated.get(key)

        if (
            current is None
            or signal.materiality_score > current.materiality_score
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
