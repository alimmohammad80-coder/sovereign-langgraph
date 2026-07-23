from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any, Iterable


@dataclass(frozen=True)
class ConvergenceResult:
    convergence_level: str
    convergence_score: float
    elevated_domains: list[str]
    deteriorating_domains: list[str]
    reinforcing_pairs: list[dict[str, Any]]
    findings: list[dict[str, Any]]


class ConvergenceAnalyzer:
    """
    Detects supported cross-domain convergence.

    This analyzer does not infer unsupported causal chains. It only
    identifies reinforcement when multiple supplied assessments are
    elevated and/or deteriorating at the same time.
    """

    ELEVATED_THRESHOLD = 50.0
    HIGH_THRESHOLD = 70.0

    @staticmethod
    def _score(value: Any) -> float:
        try:
            return max(0.0, min(100.0, float(value)))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _domain_key(
        assessment: dict[str, Any],
    ) -> str:
        return str(
            assessment.get("sector")
            or assessment.get("agent_key")
            or assessment.get("domain")
            or ""
        ).strip()

    @staticmethod
    def _direction(
        assessment: dict[str, Any],
    ) -> str:
        direct = assessment.get("direction")

        if isinstance(direct, str) and direct.strip():
            return direct.strip().lower()

        forecast = assessment.get("forecast") or assessment.get(
            "forecast_probabilities"
        )

        if not isinstance(forecast, dict):
            return "unknown"

        values: list[float] = []

        for value in forecast.values():
            try:
                values.append(float(value))
            except (TypeError, ValueError):
                continue

        if len(values) < 2:
            return "unknown"

        delta = values[-1] - values[0]

        if delta >= 3:
            return "deteriorating"

        if delta <= -3:
            return "improving"

        return "stable"

    def analyze(
        self,
        assessments: Iterable[dict[str, Any]],
    ) -> ConvergenceResult:
        normalized: list[dict[str, Any]] = []

        for assessment in assessments:
            if not isinstance(assessment, dict):
                continue

            domain = self._domain_key(assessment)

            if not domain:
                continue

            normalized.append(
                {
                    "domain": domain,
                    "risk_score": self._score(
                        assessment.get("risk_score")
                    ),
                    "confidence": self._score(
                        assessment.get("confidence")
                    ),
                    "direction": self._direction(
                        assessment
                    ),
                }
            )

        elevated = [
            item
            for item in normalized
            if item["risk_score"] >= self.ELEVATED_THRESHOLD
        ]

        deteriorating = [
            item
            for item in elevated
            if item["direction"] == "deteriorating"
        ]

        reinforcing_pairs: list[dict[str, Any]] = []

        for left, right in combinations(elevated, 2):
            pair_score = (
                left["risk_score"]
                + right["risk_score"]
            ) / 2

            both_deteriorating = (
                left["direction"] == "deteriorating"
                and right["direction"] == "deteriorating"
            )

            if both_deteriorating:
                pair_score += 8

            if (
                left["risk_score"] >= self.HIGH_THRESHOLD
                and right["risk_score"] >= self.HIGH_THRESHOLD
            ):
                pair_score += 5

            reinforcing_pairs.append(
                {
                    "domains": [
                        left["domain"],
                        right["domain"],
                    ],
                    "score": round(
                        min(100.0, pair_score),
                        2,
                    ),
                    "both_deteriorating": (
                        both_deteriorating
                    ),
                }
            )

        reinforcing_pairs.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        elevated_count = len(elevated)
        deteriorating_count = len(deteriorating)

        convergence_score = min(
            100.0,
            elevated_count * 14
            + deteriorating_count * 10
            + sum(
                max(
                    0.0,
                    item["risk_score"] - 50.0,
                )
                * 0.20
                for item in elevated
            ),
        )

        if convergence_score >= 75:
            convergence_level = "strong"
        elif convergence_score >= 50:
            convergence_level = "moderate"
        elif convergence_score >= 25:
            convergence_level = "limited"
        else:
            convergence_level = "minimal"

        findings: list[dict[str, Any]] = []

        if elevated_count >= 2:
            findings.append(
                {
                    "type": "multi_domain_elevation",
                    "domains": [
                        item["domain"]
                        for item in elevated
                    ],
                    "judgment": (
                        "Multiple domains are elevated, indicating "
                        "potential compound strategic pressure."
                    ),
                }
            )

        if deteriorating_count >= 2:
            findings.append(
                {
                    "type": "shared_deterioration",
                    "domains": [
                        item["domain"]
                        for item in deteriorating
                    ],
                    "judgment": (
                        "Multiple elevated domains show a "
                        "deteriorating trajectory."
                    ),
                }
            )

        return ConvergenceResult(
            convergence_level=convergence_level,
            convergence_score=round(
                convergence_score,
                2,
            ),
            elevated_domains=[
                item["domain"]
                for item in elevated
            ],
            deteriorating_domains=[
                item["domain"]
                for item in deteriorating
            ],
            reinforcing_pairs=reinforcing_pairs,
            findings=findings,
        )
