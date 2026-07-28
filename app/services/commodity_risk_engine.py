from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.services.supply_chain_risk_history import (
    build_risk_snapshot,
    calculate_confidence,
)

MODEL_VERSION = "sc-commodity-risk-v1"


ALIASES = {
    "advanced semiconductors": {
        "advanced semiconductors",
        "electronic integrated circuits / semiconductors",
        "semiconductors",
    },
    "crude oil": {
        "crude oil",
        "crude petroleum oils",
        "petroleum oils",
    },
    "lng": {
        "lng",
        "petroleum gases and lng",
        "liquefied natural gas",
    },
    "lithium-ion batteries": {
        "lithium-ion batteries",
        "electric accumulators / lithium-ion batteries",
    },
    "wheat": {
        "wheat",
        "wheat and meslin",
    },
}


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def normalize_name(value: str | None) -> str:
    return str(value or "").strip().lower()


def canonical_commodity_name(value: str | None) -> str:
    normalized = normalize_name(value)

    for canonical, aliases in ALIASES.items():
        if normalized in aliases:
            return canonical

    return normalized


def classify_severity(score: float) -> str:
    if score >= 85:
        return "Critical"
    if score >= 70:
        return "High"
    if score >= 60:
        return "Elevated"
    if score >= 40:
        return "Guarded"
    return "Low"


def weighted_average(values: list[tuple[float, float]]) -> float | None:
    valid = [
        (float(value), float(weight))
        for value, weight in values
        if weight > 0
    ]

    if not valid:
        return None

    total_weight = sum(weight for _, weight in valid)

    if total_weight <= 0:
        return None

    return round(
        sum(value * weight for value, weight in valid) / total_weight,
        1,
    )


def calculate_chokepoint_exposure(
    rows: list[dict[str, Any]],
    maritime_lookup: dict[str, dict[str, Any]],
) -> tuple[float | None, float | None, str | None]:
    weighted = []
    concentration_values = []

    strongest_driver = None
    strongest_strength = -1.0

    for row in rows:
        chokepoint_name = str(
            row.get("chokepoint_name") or ""
        ).strip()

        dependency_pct = float(
            row.get("dependency_pct") or 0
        )

        if not chokepoint_name:
            continue

        maritime = maritime_lookup.get(
            chokepoint_name.lower()
        )

        if not maritime:
            continue

        risk_score = maritime.get("risk_score")

        if risk_score is None:
            continue

        risk_score = float(risk_score)

        weight = max(
            clamp(dependency_pct) / 100.0,
            0.10,
        )

        weighted.append((
            risk_score,
            weight,
        ))

        concentration_values.append(
            clamp(dependency_pct)
        )

        strength = risk_score * weight

        if strength > strongest_strength:
            strongest_strength = strength
            strongest_driver = (
                f"{chokepoint_name} exposure at "
                f"{dependency_pct:.0f}% "
                f"(maritime risk {risk_score:.1f})"
            )

    exposure_score = weighted_average(weighted)

    concentration_score = (
        round(max(concentration_values), 1)
        if concentration_values
        else None
    )

    return (
        exposure_score,
        concentration_score,
        strongest_driver,
    )


def calculate_structural_chokepoint_exposure(
    rows: list[dict[str, Any]],
    maritime_lookup: dict[str, dict[str, Any]],
) -> tuple[float | None, str | None]:
    """
    Use structural chokepoint mappings when quantified dependency
    percentages are unavailable.

    These relationships contribute risk evidence but do NOT invent
    a dependency percentage.
    """

    risks = []
    strongest_driver = None
    strongest_score = -1.0

    for row in rows:
        chokepoint_name = str(
            row.get("chokepoint_name") or ""
        ).strip()

        if not chokepoint_name:
            continue

        maritime = maritime_lookup.get(
            chokepoint_name.lower()
        )

        if not maritime:
            continue

        risk_score = maritime.get("risk_score")

        if risk_score is None:
            continue

        risk_score = float(risk_score)
        risks.append(risk_score)

        if risk_score > strongest_score:
            strongest_score = risk_score
            strongest_driver = (
                f"Structural exposure to {chokepoint_name} "
                f"(maritime risk {risk_score:.1f})"
            )

    if not risks:
        return None, None

    return (
        round(sum(risks) / len(risks), 1),
        strongest_driver,
    )



def calculate_alternative_supply_resilience(
    rows: list[dict[str, Any]],
) -> tuple[float | None, str | None]:
    if not rows:
        return None, None

    scores = []
    strongest = None
    best_resilience = -1.0

    for row in rows:
        capacity = float(
            row.get("available_capacity_pct") or 0
        )

        lead_time = float(
            row.get("lead_time_days") or 90
        )

        geopolitical_risk = float(
            row.get("geopolitical_risk_score") or 50
        )

        capacity_component = clamp(capacity)

        lead_time_component = clamp(
            100 - min(lead_time, 120) / 120 * 100
        )

        geopolitical_component = clamp(
            100 - geopolitical_risk
        )

        resilience = round(
            capacity_component * 0.45
            + lead_time_component * 0.25
            + geopolitical_component * 0.30,
            1,
        )

        scores.append(resilience)

        if resilience > best_resilience:
            best_resilience = resilience

            supplier = (
                row.get("supplier_company")
                or row.get("supplier_country")
                or "alternative supplier"
            )

            strongest = (
                f"Alternative supply via {supplier}: "
                f"{capacity:.0f}% available capacity, "
                f"{lead_time:.0f}d lead time"
            )

    return round(max(scores), 1), strongest


def calculate_live_signal_score(
    events: list[dict[str, Any]],
) -> float | None:
    if not events:
        return None

    values = [
        float(event.get("severity_score") or 50)
        for event in events
    ]

    return round(
        sum(values) / len(values),
        1,
    )


def build_commodity_assessment(
    *,
    commodity: dict[str, Any],
    quantitative_exposures: list[dict[str, Any]],
    structural_exposures: list[dict[str, Any]],
    alternatives: list[dict[str, Any]],
    live_events: list[dict[str, Any]],
    maritime_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    commodity_name = str(
        commodity.get("commodity_name") or ""
    ).strip()

    baseline = float(
        commodity.get("baseline_risk_score")
        or 50
    )

    previous = float(
        commodity.get("risk_score")
        or baseline
    )

    chokepoint_score, concentration_score, chokepoint_driver = (
        calculate_chokepoint_exposure(
            quantitative_exposures,
            maritime_lookup,
        )
    )

    structural_chokepoint_score, structural_driver = (
        calculate_structural_chokepoint_exposure(
            structural_exposures,
            maritime_lookup,
        )
    )

    resilience_score, resilience_driver = (
        calculate_alternative_supply_resilience(
            alternatives
        )
    )

    live_signal_score = calculate_live_signal_score(
        live_events
    )

    # -----------------------------------------------------
    # CURRENT COMMODITY RISK
    #
    # Dependency percentages control transmission strength;
    # they are NOT themselves risk scores.
    #
    # Quantified chokepoint exposure takes precedence.
    # Structural mappings are used as lower-confidence evidence.
    # -----------------------------------------------------

    if chokepoint_score is not None:
        if live_signal_score is not None:
            raw_risk = (
                baseline * 0.45
                + chokepoint_score * 0.35
                + live_signal_score * 0.20
            )
        else:
            raw_risk = (
                baseline * 0.55
                + chokepoint_score * 0.45
            )

    elif structural_chokepoint_score is not None:
        if live_signal_score is not None:
            raw_risk = (
                baseline * 0.55
                + structural_chokepoint_score * 0.25
                + live_signal_score * 0.20
            )
        else:
            raw_risk = (
                baseline * 0.70
                + structural_chokepoint_score * 0.30
            )

    elif live_signal_score is not None:
        raw_risk = (
            baseline * 0.75
            + live_signal_score * 0.25
        )

    else:
        raw_risk = baseline

    # Alternative supply represents resilience.
    # Keep the first-generation mitigation deliberately bounded so
    # available substitutes cannot erase structural exposure.
    resilience_reduction = 0.0

    if resilience_score is not None:
        resilience_reduction = min(
            resilience_score * 0.08,
            5.0,
        )

    current = round(
        clamp(
            raw_risk - resilience_reduction
        ),
        1,
    )

    mapped_dimensions = sum([
        bool(quantitative_exposures),
        bool(structural_exposures),
        bool(alternatives),
        bool(live_events),
    ])

    relationship_count = (
        len(quantitative_exposures)
        + len(structural_exposures)
        + len(alternatives)
        + len(live_events)
    )

    distinct_sources = len({
        normalize_name(
            event.get("source")
        )
        for event in live_events
        if event.get("source")
    })

    avg_live_confidence = (
        sum(
            float(
                event.get("confidence_score")
                or 60
            )
            for event in live_events
        ) / len(live_events)
        if live_events
        else 70.0
    )

    confidence = calculate_confidence(
        source_count=max(
            relationship_count,
            len(live_events),
        ),
        fresh_source_count=len(
            live_events
        ),
        independent_source_count=min(
            max(
                distinct_sources,
                mapped_dimensions,
            ),
            5,
        ),
        relationship_coverage=(
            mapped_dimensions / 4.0
        ) * 100.0,
        source_reliability=(
            avg_live_confidence
        ),
    )

    snapshot = build_risk_snapshot(
        entity_type="commodity",
        entity_name=commodity_name,
        baseline_risk_score=baseline,
        previous_risk_score=previous,
        signal_score=live_signal_score or 0.0,
        dependency_score=(
            chokepoint_score
            if chokepoint_score is not None
            else baseline
        ),
        impact_score=float(
            commodity.get(
                "strategic_importance"
            )
            or baseline
        ),
        confidence_score=confidence,
        current_risk_score=current,
    )

    drivers = [
        driver
        for driver in (
            chokepoint_driver,
            structural_driver,
            resilience_driver,
        )
        if driver
    ]

    if drivers:
        dominant_driver = drivers[0]

    elif relationship_count == 0:
        dominant_driver = (
            "Insufficient mapped commodity dependencies"
        )

    else:
        dominant_driver = (
            "Structural commodity exposure"
        )

    return {
        "commodity": commodity_name,
        "baseline_score": round(
            baseline,
            1,
        ),
        "previous_score": round(
            previous,
            1,
        ),
        "new_score": current,
        "severity": classify_severity(
            current
        ),
        "score_delta": snapshot[
            "score_delta"
        ],
        "direction": snapshot[
            "direction"
        ],
        "chokepoint_exposure_score": (
            chokepoint_score
        ),
        "concentration_score": (
            concentration_score
        ),
        "alternative_supply_score": (
            resilience_score
        ),
        "live_signal_score": (
            live_signal_score
        ),
        "confidence_score": confidence,
        "dominant_driver": (
            dominant_driver
        ),
        "relationship_count": (
            relationship_count
        ),
        "model_version": MODEL_VERSION,
        "last_calculated_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        "snapshot": {
            **snapshot,
            "model_version": MODEL_VERSION,
        },
    }


def calculate_all_commodities(
    *,
    commodities: list[dict[str, Any]],
    quantitative_exposures: list[dict[str, Any]],
    structural_exposures: list[dict[str, Any]],
    alternatives: list[dict[str, Any]],
    live_events: list[dict[str, Any]],
    maritime_nodes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    maritime_lookup = {}

    for row in maritime_nodes:
        for key in (
            row.get("name"),
            row.get("canonical_name"),
        ):
            normalized = normalize_name(key)

            if normalized:
                maritime_lookup[normalized] = row

    quantitative_by_commodity = defaultdict(list)
    structural_by_commodity = defaultdict(list)
    alternatives_by_commodity = defaultdict(list)
    events_by_commodity = defaultdict(list)

    for row in quantitative_exposures:
        key = canonical_commodity_name(
            row.get("commodity")
        )

        if key:
            quantitative_by_commodity[
                key
            ].append(row)

    for row in structural_exposures:
        key = canonical_commodity_name(
            row.get("commodity_name")
        )

        if key:
            structural_by_commodity[
                key
            ].append(row)

    for row in alternatives:
        key = canonical_commodity_name(
            row.get("commodity")
        )

        if key:
            alternatives_by_commodity[
                key
            ].append(row)

    for row in live_events:
        key = canonical_commodity_name(
            row.get("matched_commodity")
        )

        if key:
            events_by_commodity[
                key
            ].append(row)

    assessments = []

    for commodity in commodities:
        commodity_name = str(
            commodity.get(
                "commodity_name"
            ) or ""
        ).strip()

        if not commodity_name:
            continue

        key = canonical_commodity_name(
            commodity_name
        )

        assessments.append(
            build_commodity_assessment(
                commodity=commodity,
                quantitative_exposures=(
                    quantitative_by_commodity.get(
                        key,
                        [],
                    )
                ),
                structural_exposures=(
                    structural_by_commodity.get(
                        key,
                        [],
                    )
                ),
                alternatives=(
                    alternatives_by_commodity.get(
                        key,
                        [],
                    )
                ),
                live_events=(
                    events_by_commodity.get(
                        key,
                        [],
                    )
                ),
                maritime_lookup=(
                    maritime_lookup
                ),
            )
        )

    return assessments
