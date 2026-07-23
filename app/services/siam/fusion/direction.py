from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class DirectionResult:
    strategic_direction: str
    direction_score: float
    deteriorating_domains: list[str]
    improving_domains: list[str]
    stable_domains: list[str]
    unknown_domains: list[str]


class DirectionAnalyzer:
    """
    Infers the overall strategic trajectory from supplied assessments.

    It preserves domain judgments and does not infer unsupported events.
    """

    @staticmethod
    def _domain(
        assessment: dict[str, Any],
    ) -> str:
        return str(
            assessment.get("sector")
            or assessment.get("agent_key")
            or assessment.get("domain")
            or "unknown"
        ).strip()

    @staticmethod
    def _risk_score(value: Any) -> float:
        try:
            return max(
                0.0,
                min(100.0, float(value)),
            )
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def _direction(
        cls,
        assessment: dict[str, Any],
    ) -> str:
        direct = assessment.get("direction")

        if isinstance(direct, str):
            normalized = direct.strip().lower()

            aliases = {
                "worsening": "deteriorating",
                "declining": "deteriorating",
                "negative": "deteriorating",
                "recovering": "improving",
                "positive": "improving",
                "neutral": "stable",
                "unchanged": "stable",
            }

            normalized = aliases.get(
                normalized,
                normalized,
            )

            if normalized in {
                "deteriorating",
                "improving",
                "stable",
            }:
                return normalized

        forecast = (
            assessment.get("forecast")
            or assessment.get(
                "forecast_probabilities"
            )
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
    ) -> DirectionResult:
        deteriorating: list[str] = []
        improving: list[str] = []
        stable: list[str] = []
        unknown: list[str] = []

        weighted_direction = 0.0
        total_weight = 0.0

        for assessment in assessments:
            if not isinstance(assessment, dict):
                continue

            domain = self._domain(assessment)
            direction = self._direction(assessment)
            risk_score = self._risk_score(
                assessment.get("risk_score")
            )

            weight = max(
                0.25,
                risk_score / 100.0,
            )

            if direction == "deteriorating":
                deteriorating.append(domain)
                weighted_direction += weight
                total_weight += weight

            elif direction == "improving":
                improving.append(domain)
                weighted_direction -= weight
                total_weight += weight

            elif direction == "stable":
                stable.append(domain)
                total_weight += weight

            else:
                unknown.append(domain)

        normalized_score = (
            weighted_direction / total_weight
            if total_weight
            else 0.0
        )

        direction_score = round(
            max(
                -100.0,
                min(100.0, normalized_score * 100),
            ),
            2,
        )

        known_count = (
            len(deteriorating)
            + len(improving)
            + len(stable)
        )

        opposing_change = (
            bool(deteriorating)
            and bool(improving)
        )

        if known_count == 0:
            strategic_direction = "unknown"

        elif opposing_change:
            strategic_direction = "volatile"

        elif direction_score >= 55:
            strategic_direction = (
                "rapid deterioration"
            )

        elif direction_score >= 15:
            strategic_direction = "deteriorating"

        elif direction_score <= -55:
            strategic_direction = "recovering"

        elif direction_score <= -15:
            strategic_direction = "improving"

        else:
            strategic_direction = "stable"

        return DirectionResult(
            strategic_direction=strategic_direction,
            direction_score=direction_score,
            deteriorating_domains=deteriorating,
            improving_domains=improving,
            stable_domains=stable,
            unknown_domains=unknown,
        )
