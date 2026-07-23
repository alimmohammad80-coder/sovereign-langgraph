from __future__ import annotations

from app.agents.base_agent import AgentSignal


CENTRAL_ASIA_ENERGY_BASELINES = [
    {
        "id": "cpc-kazakhstan",
        "headline": "Kazakhstan oil exports remain highly dependent on the CPC route",
        "summary": (
            "Kazakhstan relies heavily on the Caspian Pipeline Consortium "
            "export corridor for crude oil shipments, creating structural "
            "exposure to route disruption and Black Sea transit risk."
        ),
        "severity": 68.0,
        "confidence": 82.0,
        "signal_type": "energy_export_route_risk",
        "source_key": "Sovereign Energy Infrastructure Baseline",
        "tags": ["kazakhstan", "oil", "cpc", "export_route"],
    },
    {
        "id": "central-asia-china-gas",
        "headline": "Central Asia-China gas pipelines are a critical regional export corridor",
        "summary": (
            "Turkmenistan, Uzbekistan, and Kazakhstan depend on the "
            "Central Asia-China pipeline system for significant gas export "
            "flows, creating structural concentration risk."
        ),
        "severity": 64.0,
        "confidence": 80.0,
        "signal_type": "energy_export_route_risk",
        "source_key": "Sovereign Energy Infrastructure Baseline",
        "tags": [
            "turkmenistan",
            "uzbekistan",
            "kazakhstan",
            "natural_gas",
            "china",
        ],
    },
    {
        "id": "central-asia-hydropower",
        "headline": "Kyrgyzstan and Tajikistan retain high structural hydropower dependence",
        "summary": (
            "Heavy reliance on hydropower leaves Kyrgyzstan and Tajikistan "
            "exposed to seasonal water availability and cross-border water "
            "management pressures."
        ),
        "severity": 56.0,
        "confidence": 78.0,
        "signal_type": "energy_system_dependency",
        "source_key": "Sovereign Energy Infrastructure Baseline",
        "tags": [
            "kyrgyzstan",
            "tajikistan",
            "hydropower",
            "water_security",
        ],
    },
]


def collect_regional_energy_baselines(
    region: str | None,
) -> list[AgentSignal]:
    if str(region or "").strip().lower() != "central asia":
        return []

    signals: list[AgentSignal] = []

    for row in CENTRAL_ASIA_ENERGY_BASELINES:
        severity = float(row["severity"])
        confidence = float(row["confidence"])

        signals.append(
            AgentSignal(
                signal_id=f"regional-energy-{row['id']}",
                domain="energy",
                signal_type=row["signal_type"],
                headline=row["headline"],
                summary=row["summary"],
                country_iso3=None,
                country_name=None,
                region="Central Asia",
                severity=severity,
                relevance=95.0,
                confidence=confidence,
                source_reliability=82.0,
                materiality_score=round(
                    severity * 0.55
                    + confidence * 0.20
                    + 95.0 * 0.15
                    + 82.0 * 0.10,
                    2,
                ),
                direction="neutral",
                source_key=row["source_key"],
                is_structural=True,
                freshness_type="structural",
                tags=row["tags"],
            )
        )

    return signals
