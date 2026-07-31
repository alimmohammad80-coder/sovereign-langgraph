from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Iterable

from app.schemas.sews import (
    AssessmentRequest,
    AssessmentResult,
    ConfidenceBreakdown,
    IndicatorClass,
    IndicatorInput,
    IndicatorStatus,
    ProblemState,
)


STATE_ORDER = {
    ProblemState.DORMANT: 0,
    ProblemState.WATCH: 1,
    ProblemState.ADVISORY: 2,
    ProblemState.WARNING: 3,
    ProblemState.CRITICAL: 4,
}


def _logit(p: float) -> float:
    return math.log(p / (1.0 - p))


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _decay_multiplier(age_days: float, half_life_days: float) -> float:
    return 0.5 ** (age_days / half_life_days)


def _status_strength(indicator: IndicatorInput) -> float:
    mapping = {
        IndicatorStatus.QUIET: 0.0,
        IndicatorStatus.STIRRING: 0.45,
        IndicatorStatus.ACTIVE: 1.0,
        IndicatorStatus.CONTRADICTING: 1.0,
        IndicatorStatus.DARK: 0.70,
    }
    return mapping[indicator.status]


def _signed_contribution(indicator: IndicatorInput) -> float:
    strength = _status_strength(indicator)
    decay = _decay_multiplier(
        indicator.age_days,
        indicator.decay_half_life_days,
    )
    z_factor = 1.0
    if indicator.baseline_z is not None:
        z_factor = min(abs(indicator.baseline_z) / 2.0, 1.5)

    contribution = indicator.weight * strength * decay * z_factor

    is_negative = (
        indicator.indicator_class == IndicatorClass.CONTRA
        or indicator.status == IndicatorStatus.CONTRADICTING
    )
    return -contribution if is_negative else contribution


def probability_band(probability: float) -> str:
    pct = probability * 100
    if pct < 20:
        return "0–20%"
    if pct < 40:
        return "20–40%"
    if pct < 60:
        return "40–60%"
    if pct < 75:
        return "60–75%"
    if pct < 90:
        return "75–90%"
    return "90–100%"


def confidence_level(score: float) -> str:
    if score >= 75:
        return "HIGH"
    if score >= 50:
        return "MEDIUM"
    return "LOW"


def compute_confidence(
    indicators: Iterable[IndicatorInput],
    model_agreement: float,
) -> ConfidenceBreakdown:
    items = list(indicators)
    total = max(len(items), 1)
    reporting = [i for i in items if i.reporting]
    dark = [i for i in items if i.status == IndicatorStatus.DARK]

    indicator_coverage = len(reporting) / total
    collection_integrity = max(0.0, 1.0 - (len(dark) / total))

    unique_domains_proxy = sum(i.source_domains for i in reporting)
    source_diversity = min(unique_domains_proxy / max(total * 2, 1), 1.0)

    freshness_values = [
        _decay_multiplier(i.age_days, max(i.decay_half_life_days, 1))
        for i in reporting
    ]
    freshness = (
        sum(freshness_values) / len(freshness_values)
        if freshness_values
        else 0.0
    )

    return ConfidenceBreakdown(
        source_diversity=round(source_diversity, 4),
        indicator_coverage=round(indicator_coverage, 4),
        collection_integrity=round(collection_integrity, 4),
        model_agreement=round(model_agreement, 4),
        freshness=round(freshness, 4),
    )


def confidence_score(breakdown: ConfidenceBreakdown) -> float:
    score = 100 * (
        0.25 * breakdown.source_diversity
        + 0.30 * breakdown.indicator_coverage
        + 0.20 * breakdown.collection_integrity
        + 0.15 * breakdown.model_agreement
        + 0.10 * breakdown.freshness
    )
    return round(max(0.0, min(score, 100.0)), 1)


def recommend_state(
    probability: float,
    confidence: float,
    severity: float,
) -> ProblemState:
    # Explicit deterministic upward thresholds.
    # Downward hysteresis is applied separately in apply_hysteresis().
    if probability >= 0.85 and confidence >= 65 and severity >= 80:
        return ProblemState.CRITICAL
    if probability >= 0.70 and confidence >= 55 and severity >= 65:
        return ProblemState.WARNING
    if probability >= 0.50 and confidence >= 45:
        return ProblemState.ADVISORY
    if probability >= 0.30:
        return ProblemState.WATCH
    return ProblemState.DORMANT


def apply_hysteresis(
    current: ProblemState,
    recommended: ProblemState,
    probability: float,
) -> ProblemState:
    if current in (ProblemState.RESOLVED, ProblemState.FALSIFIED):
        return current

    current_rank = STATE_ORDER[current]
    next_rank = STATE_ORDER[recommended]

    # Escalation may occur immediately.
    if next_rank >= current_rank:
        return recommended

    # De-escalation requires probability to cross a lower threshold.
    down_thresholds = {
        ProblemState.CRITICAL: 0.72,
        ProblemState.WARNING: 0.58,
        ProblemState.ADVISORY: 0.42,
        ProblemState.WATCH: 0.22,
    }
    threshold = down_thresholds.get(current, 0.0)
    return recommended if probability < threshold else current


def assess(request: AssessmentRequest) -> AssessmentResult:
    contributions = []
    log_odds = _logit(request.base_rate)

    for indicator in request.indicators:
        contribution = _signed_contribution(indicator)
        log_odds += contribution
        contributions.append(
            {
                "indicator_key": indicator.indicator_key,
                "class": indicator.indicator_class.value,
                "status": indicator.status.value,
                "contribution": round(contribution, 4),
            }
        )

    probability = round(_sigmoid(log_odds), 4)
    breakdown = compute_confidence(
        request.indicators,
        request.model_agreement,
    )
    conf_score = confidence_score(breakdown)
    raw_state = recommend_state(
        probability,
        conf_score,
        request.severity_score,
    )
    final_state = apply_hysteresis(
        request.current_state,
        raw_state,
        probability,
    )

    contributions.sort(
        key=lambda item: abs(item["contribution"]),
        reverse=True,
    )

    return AssessmentResult(
        problem_key=request.problem_key,
        assessed_at=datetime.now(timezone.utc),
        probability=probability,
        probability_band=probability_band(probability),
        confidence_score=conf_score,
        confidence_level=confidence_level(conf_score),
        severity_score=request.severity_score,
        recommended_state=final_state,
        indicator_contributions=contributions,
        confidence_breakdown=breakdown,
    )
