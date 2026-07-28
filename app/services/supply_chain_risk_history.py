from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional


MODEL_VERSION = "sc-risk-v1"


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def classify_direction(delta: float, threshold: float = 2.0) -> str:
    if delta >= threshold:
        return "deteriorating"
    if delta <= -threshold:
        return "improving"
    return "stable"


def calculate_confidence(
    *,
    source_count: int = 0,
    fresh_source_count: int = 0,
    independent_source_count: int = 0,
    relationship_coverage: float = 0.0,
    source_reliability: float = 60.0,
) -> float:
    """
    Confidence measures evidence quality, not risk severity.

    Inputs are normalized into a 0-100 score.
    """

    source_depth = min(source_count / 10.0, 1.0) * 100
    freshness = (
        min(fresh_source_count / max(source_count, 1), 1.0) * 100
        if source_count
        else 0
    )
    independence = min(independent_source_count / 5.0, 1.0) * 100

    confidence = (
        source_depth * 0.20
        + freshness * 0.20
        + independence * 0.20
        + clamp(relationship_coverage) * 0.20
        + clamp(source_reliability) * 0.20
    )

    return round(clamp(confidence), 1)


def build_risk_snapshot(
    *,
    entity_type: str,
    entity_name: str,
    baseline_risk_score: float,
    previous_risk_score: Optional[float],
    signal_score: float,
    dependency_score: float,
    impact_score: float,
    confidence_score: float,
    current_risk_score: Optional[float] = None,
) -> dict[str, Any]:
    """
    Create a normalized supply-chain risk-history record.

    If current_risk_score is omitted, use a first-generation weighted model:
        baseline   40%
        signals    30%
        dependency 20%
        impact     10%

    This is intentionally explicit and versioned so we can improve the
    model later without corrupting historical interpretation.
    """

    baseline = clamp(float(baseline_risk_score))
    signals = clamp(float(signal_score))
    dependency = clamp(float(dependency_score))
    impact = clamp(float(impact_score))
    confidence = clamp(float(confidence_score))

    if current_risk_score is None:
        current = round(
            baseline * 0.40
            + signals * 0.30
            + dependency * 0.20
            + impact * 0.10,
            1,
        )
    else:
        current = round(clamp(float(current_risk_score)), 1)

    previous = current if previous_risk_score is None else clamp(
        float(previous_risk_score)
    )

    delta = round(current - previous, 1)

    # A newly evidence-backed score is an initial assessment,
    # not a genuine deterioration from the structural baseline.
    if previous_risk_score is None:
        direction = "initial"
    elif (
        abs(previous - baseline) < 0.01
        and abs(current - baseline) >= 0.1
    ):
        direction = "initial"
    else:
        direction = classify_direction(delta)

    return {
        "entity_type": entity_type,
        "entity_name": entity_name,
        "baseline_risk_score": round(baseline, 1),
        "current_risk_score": current,
        "previous_risk_score": round(previous, 1),
        "score_delta": delta,
        "signal_score": round(signals, 1),
        "dependency_score": round(dependency, 1),
        "impact_score": round(impact, 1),
        "confidence_score": round(confidence, 1),
        "direction": direction,
        "model_version": MODEL_VERSION,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }
