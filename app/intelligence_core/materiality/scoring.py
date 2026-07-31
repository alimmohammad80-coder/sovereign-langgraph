from __future__ import annotations

from dataclasses import dataclass

from app.intelligence_core.observations.schemas import (
    MaterialityLevel,
)


@dataclass(frozen=True, slots=True)
class MaterialityResult:
    score: float
    level: MaterialityLevel
    is_material: bool
    components: dict[str, float]


class MaterialityScorer:
    """
    Deterministic materiality calculation.

    Inputs:
    - severity: 0-100
    - confidence: 0-1
    - source_reliability: 0-1
    - novelty: 0-1
    - cross_module_relevance: 0-1
    """

    SEVERITY_WEIGHT = 0.35
    CONFIDENCE_WEIGHT = 0.20
    RELIABILITY_WEIGHT = 0.20
    NOVELTY_WEIGHT = 0.15
    CROSS_MODULE_WEIGHT = 0.10

    MATERIAL_THRESHOLD = 60.0

    @classmethod
    def calculate(
        cls,
        *,
        severity: float,
        confidence: float,
        source_reliability: float,
        novelty: float = 0.5,
        cross_module_relevance: float = 0.5,
    ) -> MaterialityResult:
        severity_score = cls._clamp(severity, 0.0, 100.0)
        confidence_score = cls._ratio(confidence) * 100.0
        reliability_score = cls._ratio(source_reliability) * 100.0
        novelty_score = cls._ratio(novelty) * 100.0
        cross_module_score = (
            cls._ratio(cross_module_relevance) * 100.0
        )

        score = (
            severity_score * cls.SEVERITY_WEIGHT
            + confidence_score * cls.CONFIDENCE_WEIGHT
            + reliability_score * cls.RELIABILITY_WEIGHT
            + novelty_score * cls.NOVELTY_WEIGHT
            + cross_module_score * cls.CROSS_MODULE_WEIGHT
        )

        score = round(cls._clamp(score, 0.0, 100.0), 2)

        if score >= 85:
            level = MaterialityLevel.CRITICAL
        elif score >= 70:
            level = MaterialityLevel.HIGH
        elif score >= 45:
            level = MaterialityLevel.MODERATE
        else:
            level = MaterialityLevel.LOW

        return MaterialityResult(
            score=score,
            level=level,
            is_material=score >= cls.MATERIAL_THRESHOLD,
            components={
                "severity": severity_score,
                "confidence": confidence_score,
                "source_reliability": reliability_score,
                "novelty": novelty_score,
                "cross_module_relevance": cross_module_score,
            },
        )

    @staticmethod
    def _clamp(
        value: float,
        minimum: float,
        maximum: float,
    ) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = minimum

        return max(minimum, min(maximum, number))

    @classmethod
    def _ratio(cls, value: float) -> float:
        number = cls._clamp(value, 0.0, 100.0)

        if number > 1.0:
            number /= 100.0

        return cls._clamp(number, 0.0, 1.0)
