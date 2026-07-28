from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.services.supply_chain_risk_history import (
    build_risk_snapshot,
    calculate_confidence,
)


MODEL_VERSION = "sc-maritime-risk-v1"


NODE_TYPE_VULNERABILITY = {
    "strait": 78.0,
    "canal": 82.0,
    "channel": 68.0,
    "strategic_passage": 65.0,
    "maritime_region": 55.0,
    "corridor": 58.0,
    "river_system": 62.0,
    "unclassified": 50.0,
}


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


def calculate_network_dependency(
    dependency_rows: list[dict[str, Any]],
) -> float:
    """
    Estimate network dependency from existing port-dependency relationships.

    This is NOT disruption probability.

    The score reflects:
    - how many ports depend on the maritime node
    - average dependency intensity
    - maximum dependency intensity
    """

    if not dependency_rows:
        return 0.0

    weights = [
        float(row.get("dependency_weight") or 0)
        for row in dependency_rows
    ]

    avg_weight = sum(weights) / len(weights)
    max_weight = max(weights)

    # Saturates as additional dependent ports are added.
    breadth_score = min(len(dependency_rows) / 8.0, 1.0) * 100.0

    score = (
        breadth_score * 0.35
        + avg_weight * 0.40
        + max_weight * 0.25
    )

    return round(clamp(score), 1)


def calculate_structural_importance(
    *,
    existing_importance: float | None,
    network_dependency_score: float,
    node_type: str,
) -> float:
    """
    Structural importance measures consequence if the node becomes impaired.

    Existing validated importance is preserved when present.
    Otherwise this first-generation model derives importance from network
    connectivity and maritime-node type.
    """

    if existing_importance is not None:
        return round(clamp(float(existing_importance)), 1)

    type_floor = {
        "strait": 72.0,
        "canal": 78.0,
        "channel": 62.0,
        "strategic_passage": 65.0,
        "maritime_region": 58.0,
        "corridor": 60.0,
        "river_system": 60.0,
        "unclassified": 50.0,
    }.get(node_type, 50.0)

    score = (
        network_dependency_score * 0.65
        + type_floor * 0.35
    )

    return round(clamp(score), 1)


def calculate_structural_vulnerability(
    *,
    node_type: str,
    network_dependency_score: float,
    traffic_pct: float | None,
) -> float:
    """
    First-generation structural vulnerability proxy.

    This remains explicitly model-based until richer inputs are added:
    rerouting capacity, closure alternatives, physical constraints,
    congestion, conflict exposure, climate exposure, and traffic volumes.
    """

    type_score = NODE_TYPE_VULNERABILITY.get(node_type, 50.0)

    traffic_score = (
        clamp(float(traffic_pct))
        if traffic_pct is not None
        else network_dependency_score
    )

    vulnerability = (
        type_score * 0.50
        + network_dependency_score * 0.30
        + traffic_score * 0.20
    )

    return round(clamp(vulnerability), 1)


def calculate_baseline_risk(
    *,
    existing_baseline: float | None,
    strategic_importance: float,
    structural_vulnerability: float,
    network_dependency_score: float,
) -> float:
    """
    Preserve validated historical baselines when available.

    For newly registered nodes, derive an explainable structural baseline.
    """

    if existing_baseline is not None:
        return round(clamp(float(existing_baseline)), 1)

    baseline = (
        strategic_importance * 0.40
        + structural_vulnerability * 0.40
        + network_dependency_score * 0.20
    )

    return round(clamp(baseline), 1)


def calculate_live_signal_score(
    events: list[dict[str, Any]],
    baseline_risk_score: float,
) -> float:
    if not events:
        # No observed live disruption pressure.
        # Structural risk remains represented separately by baseline_risk_score.
        return 0.0

    severities = [
        float(event.get("severity_score") or 50)
        for event in events
    ]

    return round(
        clamp(sum(severities) / len(severities)),
        1,
    )


def build_maritime_assessment(
    *,
    node: dict[str, Any],
    dependencies: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    name = str(node.get("name") or "").strip()
    node_type = str(node.get("node_type") or "unclassified").strip().lower()

    network_dependency_score = calculate_network_dependency(dependencies)

    strategic_importance = calculate_structural_importance(
        existing_importance=node.get("strategic_importance"),
        network_dependency_score=network_dependency_score,
        node_type=node_type,
    )

    structural_vulnerability = calculate_structural_vulnerability(
        node_type=node_type,
        network_dependency_score=network_dependency_score,
        traffic_pct=node.get("traffic_pct"),
    )

    baseline_risk_score = calculate_baseline_risk(
        existing_baseline=node.get("baseline_risk_score"),
        strategic_importance=strategic_importance,
        structural_vulnerability=structural_vulnerability,
        network_dependency_score=network_dependency_score,
    )

    live_signal_score = calculate_live_signal_score(
        events,
        baseline_risk_score,
    )

    previous_score = float(
        node.get("risk_score")
        or baseline_risk_score
    )

    distinct_sources = len({
        str(event.get("source") or "").strip().lower()
        for event in events
        if event.get("source")
    })

    avg_event_confidence = (
        sum(
            float(event.get("confidence_score") or 60)
            for event in events
        ) / len(events)
        if events
        else 70.0
    )

    relationship_coverage = min(
        100.0,
        30.0 + len(dependencies) * 12.0,
    )

    confidence_score = calculate_confidence(
        source_count=max(len(events), len(dependencies)),
        fresh_source_count=len(events),
        independent_source_count=min(
            max(distinct_sources, len(dependencies)),
            5,
        ),
        relationship_coverage=relationship_coverage,
        source_reliability=avg_event_confidence,
    )

    # Current maritime risk separates structural risk from observed
    # live pressure. Do not penalize a node simply because no current
    # disruption events were observed.
    if events:
        current_risk_score = round(
            clamp(
                baseline_risk_score * 0.55
                + live_signal_score * 0.25
                + network_dependency_score * 0.20
            ),
            1,
        )
    else:
        current_risk_score = round(
            clamp(
                baseline_risk_score * 0.70
                + network_dependency_score * 0.30
            ),
            1,
        )

    snapshot = build_risk_snapshot(
        entity_type="maritime_node",
        entity_name=name,
        baseline_risk_score=baseline_risk_score,
        previous_risk_score=previous_score,
        signal_score=live_signal_score,
        dependency_score=network_dependency_score,
        impact_score=strategic_importance,
        confidence_score=confidence_score,
        current_risk_score=current_risk_score,
    )

    return {
        "name": name,
        "node_type": node_type,
        "baseline_risk_score": baseline_risk_score,
        "current_risk_score": current_risk_score,
        "previous_risk_score": previous_score,
        "network_dependency_score": network_dependency_score,
        "strategic_importance": strategic_importance,
        "structural_vulnerability_score": structural_vulnerability,
        "live_signal_score": live_signal_score,
        "confidence_score": confidence_score,
        "direction": snapshot["direction"],
        "score_delta": snapshot["score_delta"],
        "severity": classify_severity(current_risk_score),
        "model_version": MODEL_VERSION,
        "last_calculated_at": datetime.now(timezone.utc).isoformat(),
        "snapshot": {
            **snapshot,
            "model_version": MODEL_VERSION,
        },
        "dependency_count": len(dependencies),
        "live_signal_count": len(events),
    }


def calculate_all_maritime_nodes(
    *,
    nodes: list[dict[str, Any]],
    dependency_rows: list[dict[str, Any]],
    live_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    dependencies_by_node: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in dependency_rows:
        name = str(row.get("dependency_name") or "").strip().lower()
        if name:
            dependencies_by_node[name].append(row)

    events_by_node: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for event in live_events:
        matched = str(
            event.get("matched_chokepoint") or ""
        ).strip().lower()

        if matched:
            events_by_node[matched].append(event)

    assessments = []

    for node in nodes:
        name = str(node.get("name") or "").strip()
        if not name:
            continue

        key = name.lower()

        assessments.append(
            build_maritime_assessment(
                node=node,
                dependencies=dependencies_by_node.get(key, []),
                events=events_by_node.get(key, []),
            )
        )

    return assessments
