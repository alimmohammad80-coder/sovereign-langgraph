from __future__ import annotations

from typing import Any


CALIBRATION_VERSION = "conflict-calibration-v1"

# Historical leave-one-conflict-out validation:
OBSERVED_RATE = 0.151163
MEAN_FORECAST = 0.151922
BRIER_SCORE = 0.128642


class ConflictForecastCalibrator:

    @staticmethod
    def calibrate_probability(
        probability: float,
    ) -> dict[str, Any]:

        probability = min(
            max(
                float(probability),
                0.0,
            ),
            1.0,
        )

        # Ratio correction derived from historical
        # out-of-sample aggregate reliability.
        correction_ratio = (
            OBSERVED_RATE
            / MEAN_FORECAST
            if MEAN_FORECAST > 0
            else 1.0
        )

        calibrated = min(
            max(
                probability
                * correction_ratio,
                0.0,
            ),
            1.0,
        )

        return {
            "raw_probability":
                round(
                    probability,
                    6,
                ),

            "calibrated_probability":
                round(
                    calibrated,
                    6,
                ),

            "calibration_version":
                CALIBRATION_VERSION,

            "method":
                "aggregate_reliability_ratio",

            "correction_ratio":
                round(
                    correction_ratio,
                    6,
                ),

            "validation": {
                "method":
                    "leave-one-conflict-out",

                "target":
                    "S0_to_S3_or_S4_next_year",

                "prediction_count":
                    2150,

                "observed_event_rate":
                    OBSERVED_RATE,

                "mean_forecast_probability":
                    MEAN_FORECAST,

                "brier_score":
                    BRIER_SCORE,
            },
        }
