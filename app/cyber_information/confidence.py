from __future__ import annotations

from .models import ConfidenceAssessment, ConfidenceLevel


def assess_confidence(
    *,
    evidence_quality: float,
    source_diversity: float,
    corroboration: float,
    analytic_uncertainty: float,
    rationale: str,
) -> ConfidenceAssessment:
    """Deterministic confidence calculation for analytic objects.

    Confidence is kept separate from severity and probability. The formula is
    intentionally explicit so it can later be calibrated against analyst review.
    """
    values = (evidence_quality, source_diversity, corroboration, analytic_uncertainty)
    if any(value < 0 or value > 1 for value in values):
        raise ValueError("confidence inputs must be between 0 and 1")

    score = (
        0.35 * evidence_quality
        + 0.20 * source_diversity
        + 0.30 * corroboration
        + 0.15 * (1.0 - analytic_uncertainty)
    )
    score = round(max(0.0, min(1.0, score)), 4)

    if score >= 0.75:
        level = ConfidenceLevel.HIGH
    elif score >= 0.45:
        level = ConfidenceLevel.MODERATE
    else:
        level = ConfidenceLevel.LOW

    return ConfidenceAssessment(
        score=score,
        level=level,
        evidence_quality=evidence_quality,
        source_diversity=source_diversity,
        corroboration=corroboration,
        analytic_uncertainty=analytic_uncertainty,
        rationale=rationale,
    )
