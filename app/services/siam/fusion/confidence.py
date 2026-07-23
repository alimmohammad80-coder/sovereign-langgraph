from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class ConfidenceResult:
    calibrated_confidence: float
    average_domain_confidence: float
    coverage_factor: float
    freshness_factor: float
    agreement_factor: float
    penalties: dict[str, float]
    rationale: list[str]


class ConfidenceCalibrator:
    """
    Produces a single SIAM confidence score from domain confidence,
    coverage, freshness, convergence, and contradiction metadata.

    This calibrates confidence only. It does not alter strategic risk.
    """

    def __init__(
        self,
        *,
        expected_domain_count: int = 5,
    ) -> None:
        self.expected_domain_count = max(
            1,
            int(expected_domain_count),
        )

    @staticmethod
    def _score(value: Any) -> float:
        try:
            return max(
                0.0,
                min(100.0, float(value)),
            )
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _freshness_status(
        assessment: dict[str, Any],
    ) -> str:
        direct = assessment.get(
            "freshness_status"
        )

        if isinstance(direct, str) and direct.strip():
            return direct.strip().lower()

        payload = assessment.get(
            "presentation_payload"
        )

        if isinstance(payload, dict):
            value = payload.get(
                "freshness_status"
            )

            if isinstance(value, str):
                return value.strip().lower()

        return "unknown"

    @classmethod
    def _freshness_weight(
        cls,
        assessment: dict[str, Any],
    ) -> float:
        status = cls._freshness_status(
            assessment
        )

        weights = {
            "fresh": 1.0,
            "current": 1.0,
            "recent": 0.9,
            "mixed": 0.8,
            "stale": 0.65,
            "expired": 0.4,
            "unknown": 0.7,
        }

        return weights.get(status, 0.7)

    def calibrate(
        self,
        assessments: Iterable[dict[str, Any]],
        *,
        convergence_score: float = 0.0,
        contradiction_score: float = 0.0,
    ) -> ConfidenceResult:
        items = [
            item
            for item in assessments
            if isinstance(item, dict)
        ]

        if not items:
            return ConfidenceResult(
                calibrated_confidence=0.0,
                average_domain_confidence=0.0,
                coverage_factor=0.0,
                freshness_factor=0.0,
                agreement_factor=0.0,
                penalties={
                    "missing_domain_penalty": 100.0,
                    "stale_evidence_penalty": 0.0,
                    "contradiction_penalty": 0.0,
                },
                rationale=[
                    "No domain assessments were available."
                ],
            )

        confidences = [
            self._score(
                item.get("confidence")
            )
            for item in items
        ]

        average_confidence = (
            sum(confidences)
            / len(confidences)
        )

        available_count = len(items)

        coverage_factor = min(
            1.0,
            available_count
            / self.expected_domain_count,
        )

        freshness_weights = [
            self._freshness_weight(item)
            for item in items
        ]

        freshness_factor = (
            sum(freshness_weights)
            / len(freshness_weights)
        )

        normalized_convergence = (
            self._score(convergence_score)
            / 100.0
        )

        normalized_contradiction = (
            self._score(contradiction_score)
            / 100.0
        )

        agreement_factor = max(
            0.55,
            min(
                1.05,
                0.85
                + normalized_convergence * 0.20
                - normalized_contradiction * 0.25,
            ),
        )

        missing_domain_penalty = (
            1.0 - coverage_factor
        ) * 20.0

        stale_evidence_penalty = (
            1.0 - freshness_factor
        ) * 15.0

        contradiction_penalty = (
            normalized_contradiction
            * 12.0
        )

        calibrated = (
            average_confidence
            * coverage_factor
            * freshness_factor
            * agreement_factor
        )

        calibrated -= contradiction_penalty

        calibrated_confidence = round(
            self._score(calibrated),
            2,
        )

        rationale = [
            (
                f"{available_count} of "
                f"{self.expected_domain_count} expected "
                "domain assessments were available."
            ),
            (
                "Average supplied domain confidence was "
                f"{average_confidence:.1f}/100."
            ),
            (
                "Average evidence freshness factor was "
                f"{freshness_factor:.2f}."
            ),
        ]

        if convergence_score >= 50:
            rationale.append(
                "Cross-domain convergence increased analytical agreement."
            )

        if contradiction_score >= 20:
            rationale.append(
                "Material contradictions reduced fused confidence."
            )

        if coverage_factor < 1.0:
            rationale.append(
                "Incomplete domain coverage reduced fused confidence."
            )

        return ConfidenceResult(
            calibrated_confidence=calibrated_confidence,
            average_domain_confidence=round(
                average_confidence,
                2,
            ),
            coverage_factor=round(
                coverage_factor,
                4,
            ),
            freshness_factor=round(
                freshness_factor,
                4,
            ),
            agreement_factor=round(
                agreement_factor,
                4,
            ),
            penalties={
                "missing_domain_penalty": round(
                    missing_domain_penalty,
                    2,
                ),
                "stale_evidence_penalty": round(
                    stale_evidence_penalty,
                    2,
                ),
                "contradiction_penalty": round(
                    contradiction_penalty,
                    2,
                ),
            },
            rationale=rationale,
        )
