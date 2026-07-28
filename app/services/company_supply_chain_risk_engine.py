from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.services.supply_chain_risk_history import (
    build_risk_snapshot,
    calculate_confidence,
)


MODEL_VERSION = "sc-company-risk-v1"


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


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
    valid = [(float(v), float(w)) for v, w in values if w > 0]

    if not valid:
        return None

    total_weight = sum(weight for _, weight in valid)

    if total_weight <= 0:
        return None

    return round(
        sum(value * weight for value, weight in valid) / total_weight,
        1,
    )


def calculate_port_exposure(
    rows: list[dict[str, Any]],
    port_lookup: dict[str, dict[str, Any]],
) -> tuple[float | None, str | None]:
    weighted = []
    strongest = None
    strongest_value = -1.0

    for row in rows:
        name = str(row.get("port_name") or "").strip()
        dependency = float(row.get("dependency_pct") or 0)

        port = port_lookup.get(name.lower())
        if not port:
            continue

        risk = port.get("risk_score")
        if risk is None:
            continue

        risk = float(risk)
        weight = clamp(dependency) / 100.0

        weighted.append((risk, weight))

        driver_strength = risk * weight
        if driver_strength > strongest_value:
            strongest_value = driver_strength
            strongest = (
                f"{name} exposure at {dependency:.0f}% "
                f"(port risk {risk:.1f})"
            )

    return weighted_average(weighted), strongest


def calculate_supplier_exposure(
    rows: list[dict[str, Any]],
    supplier_risk_lookup: dict[str, float],
) -> tuple[float | None, str | None]:
    weighted = []
    strongest = None
    strongest_value = -1.0

    criticality_factor = {
        "critical": 1.00,
        "high": 0.85,
        "medium": 0.70,
        "low": 0.55,
    }

    for row in rows:
        supplier_name = str(
            row.get("supplier_name") or ""
        ).strip()

        dependency = float(
            row.get("dependency_pct") or 0
        )

        criticality = str(
            row.get("criticality") or ""
        ).strip().lower()

        supplier_risk = supplier_risk_lookup.get(
            supplier_name.lower()
        )

        if supplier_risk is None:
            continue

        factor = criticality_factor.get(
            criticality,
            0.60,
        )

        weight = (
            clamp(dependency) / 100.0
        ) * factor

        weighted.append((
            float(supplier_risk),
            weight,
        ))

        driver_strength = (
            float(supplier_risk) * weight
        )

        if driver_strength > strongest_value:
            strongest_value = driver_strength

            commodity = (
                row.get("commodity")
                or "supply"
            )

            strongest = (
                f"{supplier_name} {commodity} dependency "
                f"at {dependency:.0f}% "
                f"(supplier risk {float(supplier_risk):.1f})"
            )

    return weighted_average(weighted), strongest



def calculate_commodity_exposure(
    rows: list[dict[str, Any]],
    commodity_lookup: dict[str, dict[str, Any]],
) -> tuple[float | None, str | None]:
    """
    Propagate current commodity risk into company risk.

    Quantitative evidence uses dependency_pct or exposure_score as the
    transmission intensity.

    Structural evidence contributes moderate, lower-confidence exposure
    when a precise dependency percentage is unavailable. It does not
    invent a quantitative dependency percentage.
    """

    weighted = []
    strongest = None
    strongest_value = -1.0

    for row in rows:
        commodity_name = str(
            row.get("commodity") or ""
        ).strip()

        if not commodity_name:
            continue

        commodity = commodity_lookup.get(
            commodity_name.lower()
        )

        if not commodity:
            continue

        commodity_risk = commodity.get("risk_score")

        if commodity_risk is None:
            continue

        commodity_risk = float(commodity_risk)

        evidence_type = str(
            row.get("evidence_type") or "quantitative"
        ).strip().lower()

        exposure_score = float(
            row.get("exposure_score") or 0
        )

        dependency_pct = float(
            row.get("dependency_pct") or 0
        )

        if dependency_pct > 0:
            intensity = clamp(dependency_pct)
            evidence_weight = 1.0
            driver = (
                f"{commodity_name} dependency at "
                f"{intensity:.0f}% "
                f"(commodity risk {commodity_risk:.1f})"
            )

        elif exposure_score > 0:
            intensity = clamp(exposure_score)
            evidence_weight = 0.90
            driver = (
                f"{commodity_name} exposure intensity "
                f"{intensity:.0f}/100 "
                f"(commodity risk {commodity_risk:.1f})"
            )

        elif evidence_type == "structural":
            # Structural evidence transmits a bounded portion of current
            # commodity risk without claiming a measured dependency.
            intensity = 35.0
            evidence_weight = 0.70
            driver = (
                f"Structural exposure to {commodity_name} "
                f"(commodity risk {commodity_risk:.1f})"
            )

        else:
            intensity = 10.0
            evidence_weight = 0.50
            driver = (
                f"Limited mapped exposure to {commodity_name} "
                f"(commodity risk {commodity_risk:.1f})"
            )

        transmission_weight = max(
            intensity / 100.0,
            0.10,
        )

        final_weight = (
            transmission_weight
            * evidence_weight
        )

        weighted.append((
            commodity_risk,
            final_weight,
        ))

        transmitted_strength = (
            commodity_risk
            * final_weight
        )

        if transmitted_strength > strongest_value:
            strongest_value = transmitted_strength
            strongest = driver

    return weighted_average(weighted), strongest

def calculate_market_exposure(
    rows: list[dict[str, Any]],
) -> float | None:
    """
    Measures market concentration/exposure only.

    This is intentionally NOT interpreted as geopolitical/country risk.
    Country Intelligence will be connected in a later model version.
    """

    if not rows:
        return None

    exposures = [
        float(row.get("revenue_exposure_pct") or 0)
        for row in rows
    ]

    return round(clamp(max(exposures)), 1)


def calculate_live_company_signal(
    events: list[dict[str, Any]],
) -> float | None:
    if not events:
        return None

    values = [
        float(event.get("severity_score") or 50)
        for event in events
    ]

    return round(sum(values) / len(values), 1)


def build_company_assessment(
    *,
    company: dict[str, Any],
    ports: list[dict[str, Any]],
    suppliers: list[dict[str, Any]],
    commodities: list[dict[str, Any]],
    markets: list[dict[str, Any]],
    events: list[dict[str, Any]],
    port_lookup: dict[str, dict[str, Any]],
    company_lookup: dict[str, dict[str, Any]],
    commodity_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    company_name = str(company.get("company_name") or "").strip()

    baseline = float(
        company.get("baseline_risk_score")
        or 50
    )

    previous = float(
        company.get("risk_score")
        or baseline
    )

    port_score, port_driver = calculate_port_exposure(
        ports,
        port_lookup,
    )

    supplier_score, supplier_driver = calculate_supplier_exposure(
        suppliers,
        company_lookup,
    )

    commodity_score, commodity_driver = calculate_commodity_exposure(
        commodities,
        commodity_lookup,
    )

    market_score = calculate_market_exposure(markets)
    live_score = calculate_live_company_signal(events)

    # Only actual risk-bearing dimensions participate.
    # Missing evidence does NOT become a fake 50.
    evidence_components = []

    if port_score is not None:
        evidence_components.append((port_score, 0.35))

    if supplier_score is not None:
        evidence_components.append((supplier_score, 0.30))

    if commodity_score is not None:
        evidence_components.append((commodity_score, 0.25))

    if live_score is not None:
        evidence_components.append((live_score, 0.10))

    evidence_risk = weighted_average(evidence_components)

    if evidence_risk is None:
        current = round(clamp(baseline), 1)
    else:
        # Structural anchor + observed supply-chain evidence.
        current = round(
            clamp(
                baseline * 0.35
                + evidence_risk * 0.65
            ),
            1,
        )

    mapped_dimensions = sum([
        bool(ports),
        bool(suppliers),
        bool(commodities),
        bool(markets),
    ])

    relationship_coverage = (
        mapped_dimensions / 4.0
    ) * 100.0

    distinct_sources = len({
        str(event.get("source") or "").strip().lower()
        for event in events
        if event.get("source")
    })

    avg_live_confidence = (
        sum(
            float(event.get("confidence_score") or 60)
            for event in events
        ) / len(events)
        if events
        else 70.0
    )

    relationship_count = (
        len(ports)
        + len(suppliers)
        + len(commodities)
        + len(markets)
    )

    confidence = calculate_confidence(
        source_count=max(relationship_count, len(events)),
        fresh_source_count=len(events),
        independent_source_count=min(
            max(distinct_sources, mapped_dimensions),
            5,
        ),
        relationship_coverage=relationship_coverage,
        source_reliability=avg_live_confidence,
    )

    snapshot = build_risk_snapshot(
        entity_type="company",
        entity_name=company_name,
        baseline_risk_score=baseline,
        previous_risk_score=previous,
        signal_score=live_score or 0.0,
        dependency_score=evidence_risk or baseline,
        impact_score=float(
            company.get("strategic_importance")
            or baseline
        ),
        confidence_score=confidence,
        current_risk_score=current,
    )

    drivers = [
        driver
        for driver in (
            port_driver,
            supplier_driver,
            commodity_driver,
        )
        if driver
    ]

    if drivers:
        dominant_driver = drivers[0]
    elif relationship_count == 0:
        dominant_driver = "Insufficient mapped supply-chain dependencies"
    else:
        dominant_driver = "Structural company exposure"

    return {
        "company": company_name,
        "baseline_score": round(baseline, 1),
        "previous_score": round(previous, 1),
        "new_score": current,
        "score_delta": snapshot["score_delta"],
        "direction": snapshot["direction"],
        "severity": classify_severity(current),
        "confidence_score": confidence,
        "port_exposure_score": port_score,
        "supplier_exposure_score": supplier_score,
        "commodity_exposure_score": commodity_score,
        "market_exposure_score": market_score,
        "live_signal_score": live_score,
        "dominant_driver": dominant_driver,
        "relationship_count": relationship_count,
        "model_version": MODEL_VERSION,
        "last_calculated_at": datetime.now(timezone.utc).isoformat(),
        "snapshot": {
            **snapshot,
            "model_version": MODEL_VERSION,
        },
    }


def calculate_all_companies(
    *,
    companies: list[dict[str, Any]],
    master_ports: list[dict[str, Any]],
    commodities_master: list[dict[str, Any]],
    company_ports: list[dict[str, Any]],
    company_suppliers: list[dict[str, Any]],
    commodity_exposures: list[dict[str, Any]],
    company_markets: list[dict[str, Any]],
    live_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    port_lookup = {
        str(
            row.get("port_name") or ""
        ).strip().lower(): row
        for row in master_ports
        if row.get("port_name")
    }

    commodity_lookup = {
        str(
            row.get("commodity_name") or ""
        ).strip().lower(): row
        for row in commodities_master
        if row.get("commodity_name")
    }

    def group(rows, field):
        result = defaultdict(list)

        for row in rows:
            key = str(
                row.get(field) or ""
            ).strip().lower()

            if key:
                result[key].append(row)

        return result

    ports_by_company = group(
        company_ports,
        "company_name",
    )

    suppliers_by_company = group(
        company_suppliers,
        "company_name",
    )

    commodities_by_company = group(
        commodity_exposures,
        "company_name",
    )

    markets_by_company = group(
        company_markets,
        "company_name",
    )

    events_by_company = group(
        live_events,
        "matched_company",
    )

    # ---------------------------------------------------------
    # PASS 1
    # Calculate direct risk without supplier propagation.
    # This creates a deterministic supplier-risk reference map.
    # ---------------------------------------------------------

    direct_assessments = {}
    direct_risk_lookup = {}

    for company in companies:
        name = str(
            company.get("company_name") or ""
        ).strip()

        if not name:
            continue

        key = name.lower()

        assessment = build_company_assessment(
            company=company,
            ports=ports_by_company.get(key, []),
            suppliers=[],
            commodities=commodities_by_company.get(
                key,
                [],
            ),
            markets=markets_by_company.get(
                key,
                [],
            ),
            events=events_by_company.get(
                key,
                [],
            ),
            port_lookup=port_lookup,
            company_lookup={},
            commodity_lookup=commodity_lookup,
        )

        direct_assessments[key] = assessment
        direct_risk_lookup[key] = float(
            assessment["new_score"]
        )

    # ---------------------------------------------------------
    # PASS 2
    # Recalculate each company with supplier risk propagated
    # from the same Pass-1 state.
    # ---------------------------------------------------------

    final_assessments = []

    for company in companies:
        name = str(
            company.get("company_name") or ""
        ).strip()

        if not name:
            continue

        key = name.lower()

        ports = ports_by_company.get(key, [])
        suppliers = suppliers_by_company.get(
            key,
            [],
        )
        commodities = commodities_by_company.get(
            key,
            [],
        )
        markets = markets_by_company.get(
            key,
            [],
        )
        events = events_by_company.get(
            key,
            [],
        )

        baseline = float(
            company.get("baseline_risk_score")
            or 50
        )

        previous = float(
            company.get("risk_score")
            or baseline
        )

        port_score, port_driver = (
            calculate_port_exposure(
                ports,
                port_lookup,
            )
        )

        supplier_score, supplier_driver = (
            calculate_supplier_exposure(
                suppliers,
                direct_risk_lookup,
            )
        )

        commodity_score, commodity_driver = (
            calculate_commodity_exposure(
                commodities,
                commodity_lookup,
            )
        )

        market_score = calculate_market_exposure(
            markets
        )

        live_score = calculate_live_company_signal(
            events
        )

        evidence_components = []

        if port_score is not None:
            evidence_components.append((
                port_score,
                0.35,
            ))

        if supplier_score is not None:
            evidence_components.append((
                supplier_score,
                0.30,
            ))

        if commodity_score is not None:
            evidence_components.append((
                commodity_score,
                0.25,
            ))

        if live_score is not None:
            evidence_components.append((
                live_score,
                0.10,
            ))

        evidence_risk = weighted_average(
            evidence_components
        )

        if evidence_risk is None:
            current = round(
                clamp(baseline),
                1,
            )
        else:
            current = round(
                clamp(
                    baseline * 0.35
                    + evidence_risk * 0.65
                ),
                1,
            )

        mapped_dimensions = sum([
            bool(ports),
            bool(suppliers),
            bool(commodities),
            bool(markets),
        ])

        relationship_coverage = (
            mapped_dimensions / 4.0
        ) * 100.0

        distinct_sources = len({
            str(
                event.get("source") or ""
            ).strip().lower()
            for event in events
            if event.get("source")
        })

        avg_live_confidence = (
            sum(
                float(
                    event.get(
                        "confidence_score"
                    ) or 60
                )
                for event in events
            ) / len(events)
            if events
            else 70.0
        )

        relationship_count = (
            len(ports)
            + len(suppliers)
            + len(commodities)
            + len(markets)
        )

        confidence = calculate_confidence(
            source_count=max(
                relationship_count,
                len(events),
            ),
            fresh_source_count=len(events),
            independent_source_count=min(
                max(
                    distinct_sources,
                    mapped_dimensions,
                ),
                5,
            ),
            relationship_coverage=(
                relationship_coverage
            ),
            source_reliability=(
                avg_live_confidence
            ),
        )

        snapshot = build_risk_snapshot(
            entity_type="company",
            entity_name=name,
            baseline_risk_score=baseline,
            previous_risk_score=previous,
            signal_score=live_score or 0.0,
            dependency_score=(
                evidence_risk
                if evidence_risk is not None
                else baseline
            ),
            impact_score=float(
                company.get(
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
                port_driver,
                supplier_driver,
                commodity_driver,
            )
            if driver
        ]

        if drivers:
            dominant_driver = drivers[0]

        elif relationship_count == 0:
            dominant_driver = (
                "Insufficient mapped "
                "supply-chain dependencies"
            )

        else:
            dominant_driver = (
                "Structural company exposure"
            )

        final_assessments.append({
            "company": name,
            "baseline_score": round(
                baseline,
                1,
            ),
            "previous_score": round(
                previous,
                1,
            ),
            "new_score": current,
            "score_delta": snapshot[
                "score_delta"
            ],
            "direction": snapshot[
                "direction"
            ],
            "severity": classify_severity(
                current
            ),
            "confidence_score": confidence,
            "port_exposure_score": (
                port_score
            ),
            "supplier_exposure_score": (
                supplier_score
            ),
            "commodity_exposure_score": (
                commodity_score
            ),
            "market_exposure_score": (
                market_score
            ),
            "live_signal_score": (
                live_score
            ),
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
        })

    return final_assessments

