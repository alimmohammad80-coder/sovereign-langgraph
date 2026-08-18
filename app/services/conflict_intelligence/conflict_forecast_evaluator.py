from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)


class ConflictForecastEvaluator:

    def __init__(self) -> None:
        self.db = get_supabase_client()

    @staticmethod
    def _safe_divide(
        numerator: float,
        denominator: float,
    ) -> float | None:

        if denominator <= 0:
            return None

        return numerator / denominator

    @staticmethod
    def _metrics(
        rows: list[dict[str, Any]],
        threshold: float = 0.30,
    ) -> dict[str, Any]:

        if not rows:
            return {
                "forecast_count": 0,
                "status": "insufficient_data",
            }

        raw_brier_sum = 0.0
        calibrated_brier_sum = 0.0

        raw_absolute_error = 0.0
        calibrated_absolute_error = 0.0

        raw_probability_sum = 0.0
        calibrated_probability_sum = 0.0
        outcome_sum = 0

        true_positive = 0
        true_negative = 0
        false_positive = 0
        false_negative = 0

        for row in rows:

            outcome = (
                1
                if row.get(
                    "outcome_event_occurred"
                )
                else 0
            )

            raw = float(
                row.get(
                    "ensemble_probability"
                )
                or 0.0
            )

            calibrated_value = row.get(
                "calibrated_probability"
            )

            calibrated = (
                float(
                    calibrated_value
                )
                if calibrated_value
                is not None
                else raw
            )

            raw_brier_sum += (
                raw - outcome
            ) ** 2

            calibrated_brier_sum += (
                calibrated - outcome
            ) ** 2

            raw_absolute_error += abs(
                raw - outcome
            )

            calibrated_absolute_error += abs(
                calibrated - outcome
            )

            raw_probability_sum += raw
            calibrated_probability_sum += calibrated
            outcome_sum += outcome

            prediction = (
                calibrated >= threshold
            )

            actual = bool(
                outcome
            )

            if prediction and actual:
                true_positive += 1

            elif prediction and not actual:
                false_positive += 1

            elif not prediction and actual:
                false_negative += 1

            else:
                true_negative += 1

        count = len(rows)

        observed_rate = (
            outcome_sum / count
        )

        mean_raw = (
            raw_probability_sum
            / count
        )

        mean_calibrated = (
            calibrated_probability_sum
            / count
        )

        hit_rate = (
            ConflictForecastEvaluator
            ._safe_divide(
                true_positive,
                true_positive
                + false_negative,
            )
        )

        false_alarm_rate = (
            ConflictForecastEvaluator
            ._safe_divide(
                false_positive,
                false_positive
                + true_negative,
            )
        )

        precision = (
            ConflictForecastEvaluator
            ._safe_divide(
                true_positive,
                true_positive
                + false_positive,
            )
        )

        accuracy = (
            (
                true_positive
                + true_negative
            )
            / count
        )

        return {
            "forecast_count":
                count,

            "status":
                "evaluated",

            "observed_event_rate":
                round(
                    observed_rate,
                    6,
                ),

            "mean_raw_probability":
                round(
                    mean_raw,
                    6,
                ),

            "mean_calibrated_probability":
                round(
                    mean_calibrated,
                    6,
                ),

            "raw_brier_score":
                round(
                    raw_brier_sum
                    / count,
                    6,
                ),

            "calibrated_brier_score":
                round(
                    calibrated_brier_sum
                    / count,
                    6,
                ),

            "raw_mean_absolute_error":
                round(
                    raw_absolute_error
                    / count,
                    6,
                ),

            "calibrated_mean_absolute_error":
                round(
                    calibrated_absolute_error
                    / count,
                    6,
                ),

            "raw_calibration_gap":
                round(
                    mean_raw
                    - observed_rate,
                    6,
                ),

            "calibrated_calibration_gap":
                round(
                    mean_calibrated
                    - observed_rate,
                    6,
                ),

            "decision_threshold":
                threshold,

            "confusion_matrix": {
                "true_positive":
                    true_positive,

                "false_positive":
                    false_positive,

                "true_negative":
                    true_negative,

                "false_negative":
                    false_negative,
            },

            "hit_rate":
                (
                    round(
                        hit_rate,
                        6,
                    )
                    if hit_rate
                    is not None
                    else None
                ),

            "false_alarm_rate":
                (
                    round(
                        false_alarm_rate,
                        6,
                    )
                    if false_alarm_rate
                    is not None
                    else None
                ),

            "precision":
                (
                    round(
                        precision,
                        6,
                    )
                    if precision
                    is not None
                    else None
                ),

            "accuracy":
                round(
                    accuracy,
                    6,
                ),
        }

    def evaluate(
        self,
        threshold: float = 0.30,
        ensemble_model: str | None = None,
        limit: int = 10000,
    ) -> dict[str, Any]:

        query = (
            self.db.table(
                "conflict_forecasts"
            )
            .select(
                "run_key,"
                "conflict_id,"
                "horizon_days,"
                "ensemble_probability,"
                "calibrated_probability,"
                "calibration_version,"
                "outcome_event_occurred,"
                "outcome_state,"
                "outcome_observed_at,"
                "ensemble_model"
            )
            .not_.is_(
                "outcome_event_occurred",
                "null",
            )
            .eq(
                "active",
                True,
            )
        )

        if ensemble_model:
            query = query.eq(
                "ensemble_model",
                ensemble_model,
            )

        rows = (
            query
            .order(
                "outcome_observed_at",
                desc=True,
            )
            .limit(
                limit
            )
            .execute()
            .data
            or []
        )

        by_horizon = defaultdict(
            list
        )

        for row in rows:
            by_horizon[
                int(
                    row[
                        "horizon_days"
                    ]
                )
            ].append(
                row
            )

        horizon_metrics = {}

        for horizon in sorted(
            by_horizon
        ):
            horizon_metrics[
                str(horizon)
            ] = self._metrics(
                by_horizon[
                    horizon
                ],
                threshold,
            )

        overall = self._metrics(
            rows,
            threshold,
        )

        return {
            "evaluation_version":
                "conflict-forecast-evaluation-v1",

            "ensemble_model":
                ensemble_model
                or "all",

            "threshold":
                threshold,

            "overall":
                overall,

            "by_horizon":
                horizon_metrics,

            "outcome_count":
                len(rows),

            "calibration_ready":
                len(rows) >= 100,

            "isotonic_calibration_ready":
                len(rows) >= 500,
        }
