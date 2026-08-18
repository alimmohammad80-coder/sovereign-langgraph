from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)

from app.services.conflict_intelligence.conflict_forecast_ensemble import (
    ConflictForecastEnsemble,
)

from app.services.conflict_intelligence.conflict_forecast_calibrator import (
    ConflictForecastCalibrator,
)


class ConflictForecastPersistence:

    def __init__(self) -> None:
        self.db = get_supabase_client()
        self.ensemble = ConflictForecastEnsemble()

    @staticmethod
    def _run_key(
        conflict_id: int,
        horizon_days: int,
        generated_at: str,
    ) -> str:

        raw = (
            f"{conflict_id}|"
            f"{horizon_days}|"
            f"{generated_at}"
        )

        digest = hashlib.sha256(
            raw.encode()
        ).hexdigest()[:24].upper()

        return f"CFR-{digest}"

    def run(
        self,
        conflict_id: int,
        horizon_days: int = 30,
        lookback_days: int = 30,
    ) -> dict[str, Any]:

        forecast = (
            self.ensemble.forecast(
                conflict_id,
                horizon_days,
                lookback_days,
            )
        )

        generated_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        calibration = (
            ConflictForecastCalibrator()
            .calibrate_probability(
                forecast[
                    "ensemble_probability"
                ]
            )
        )

        frozen = (
            forecast.get(
                "frozen_conflict_match"
            )
            or {}
        )

        record = {
            "run_key":
                self._run_key(
                    conflict_id,
                    horizon_days,
                    generated_at,
                ),

            "conflict_id":
                conflict_id,

            "canonical_episode_id":
                forecast.get(
                    "canonical_episode_id"
                ),

            "generated_at":
                generated_at,

            "horizon_days":
                horizon_days,

            "lookback_days":
                lookback_days,

            "current_state":
                forecast[
                    "current_state"
                ],

            "ensemble_probability":
                forecast[
                    "ensemble_probability"
                ],

            "calibrated_probability":
                calibration[
                    "calibrated_probability"
                ],

            "calibration_version":
                calibration[
                    "calibration_version"
                ],

            "risk_band":
                forecast[
                    "risk_band"
                ],

            "confidence":
                forecast.get(
                    "confidence"
                ),

            "component_probabilities":
                forecast.get(
                    "component_probabilities"
                )
                or {},

            "model_applicability":
                forecast.get(
                    "model_applicability"
                )
                or {},

            "normalized_weights":
                forecast.get(
                    "normalized_weights"
                )
                or {},

            "state_forecast_distribution":
                forecast.get(
                    "state_forecast_distribution"
                )
                or {},

            "primary_evidence":
                forecast.get(
                    "primary_evidence"
                )
                or [],

            "frozen_conflict_id":
                frozen.get(
                    "fc_id"
                ),

            "model_versions":
                forecast.get(
                    "models"
                )
                or {},

            "ensemble_model":
                forecast[
                    "ensemble_model"
                ],

            "active":
                True,

            "review_status":
                "validated",
        }

        result = (
            self.db.table(
                "conflict_forecasts"
            )
            .insert(
                record
            )
            .execute()
            .data
            or []
        )

        stored = (
            result[0]
            if result
            else record
        )

        return {
            "forecast":
                forecast,

            "persistence": {
                "run_key":
                    stored[
                        "run_key"
                    ],

                "generated_at":
                    generated_at,

                "stored":
                    True,
            },
        }
