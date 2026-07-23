from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


FORECAST_HORIZONS = (
    "7d",
    "30d",
    "90d",
    "180d",
)


@dataclass(frozen=True)
class ForecastFusionResult:
    fused_forecast: dict[str, float]
    horizon_coverage: dict[str, int]
    domain_forecasts: list[dict[str, Any]]
    trajectory: str


class ForecastFusion:
    """
    Harmonizes deterministic domain risk outlooks.

    The output remains a fused risk outlook. It must not be described
    as a calibrated probability of a specific event unless the source
    assessments explicitly represent such probabilities.
    """

    @staticmethod
    def _score(value: Any) -> float | None:
        try:
            return max(
                0.0,
                min(100.0, float(value)),
            )
        except (TypeError, ValueError):
            return None

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
    def _forecast(
        assessment: dict[str, Any],
    ) -> dict[str, Any]:
        value = (
            assessment.get("forecast")
            or assessment.get(
                "forecast_probabilities"
            )
        )

        return value if isinstance(value, dict) else {}

    @classmethod
    def _horizon_value(
        cls,
        forecast: dict[str, Any],
        horizon: str,
    ) -> float | None:
        aliases = {
            "7d": ("7d", "7_day", "7_days"),
            "30d": ("30d", "30_day", "30_days"),
            "90d": ("90d", "90_day", "90_days"),
            "180d": (
                "180d",
                "180_day",
                "180_days",
                "6m",
            ),
        }

        for key in aliases[horizon]:
            if key in forecast:
                return cls._score(
                    forecast.get(key)
                )

        return None

    def fuse(
        self,
        assessments: Iterable[dict[str, Any]],
    ) -> ForecastFusionResult:
        items = [
            item
            for item in assessments
            if isinstance(item, dict)
        ]

        domain_forecasts: list[
            dict[str, Any]
        ] = []

        horizon_values: dict[
            str,
            list[tuple[float, float]],
        ] = {
            horizon: []
            for horizon in FORECAST_HORIZONS
        }

        for assessment in items:
            domain = self._domain(assessment)
            forecast = self._forecast(
                assessment
            )

            confidence = self._score(
                assessment.get("confidence")
            )

            confidence_weight = max(
                0.25,
                (confidence or 0.0) / 100.0,
            )

            normalized_forecast: dict[
                str,
                float
            ] = {}

            for horizon in FORECAST_HORIZONS:
                value = self._horizon_value(
                    forecast,
                    horizon,
                )

                if value is None:
                    continue

                normalized_forecast[
                    horizon
                ] = value

                horizon_values[horizon].append(
                    (
                        value,
                        confidence_weight,
                    )
                )

            domain_forecasts.append(
                {
                    "domain": domain,
                    "confidence": confidence or 0.0,
                    "forecast": normalized_forecast,
                }
            )

        fused: dict[str, float] = {}
        coverage: dict[str, int] = {}

        for horizon in FORECAST_HORIZONS:
            values = horizon_values[
                horizon
            ]
            coverage[horizon] = len(values)

            if not values:
                continue

            weighted_total = sum(
                value * weight
                for value, weight in values
            )
            total_weight = sum(
                weight
                for _, weight in values
            )

            fused[horizon] = round(
                weighted_total / total_weight,
                2,
            )

        ordered_values = [
            fused[horizon]
            for horizon in FORECAST_HORIZONS
            if horizon in fused
        ]

        if len(ordered_values) < 2:
            trajectory = "unknown"
        else:
            delta = (
                ordered_values[-1]
                - ordered_values[0]
            )

            if delta >= 8:
                trajectory = (
                    "materially deteriorating"
                )
            elif delta >= 3:
                trajectory = "deteriorating"
            elif delta <= -8:
                trajectory = (
                    "materially improving"
                )
            elif delta <= -3:
                trajectory = "improving"
            else:
                trajectory = "stable"

        return ForecastFusionResult(
            fused_forecast=fused,
            horizon_coverage=coverage,
            domain_forecasts=domain_forecasts,
            trajectory=trajectory,
        )
