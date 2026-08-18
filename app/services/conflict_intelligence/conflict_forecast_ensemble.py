from __future__ import annotations

from typing import Any

from app.services.conflict_intelligence.conflict_transition_forecaster import (
    ConflictTransitionForecaster,
)
from app.services.conflict_intelligence.pre_conflict_escalation_model import (
    PreConflictEscalationModel,
)
from app.services.conflict_intelligence.dyadic_escalation_model import (
    DyadicEscalationModel,
)
from app.services.conflict_intelligence.frozen_conflict_hazard_model import (
    FrozenConflictHazardModel,
)


UCDP_MARKOV_STATES = {
    "S0_STABLE",
    "S3_LIMITED_CONFLICT",
    "S4_WAR",
}


class ConflictForecastEnsemble:

    def __init__(self) -> None:
        self.markov = ConflictTransitionForecaster()
        self.preconflict = PreConflictEscalationModel()
        self.dyadic = DyadicEscalationModel()
        self.frozen = FrozenConflictHazardModel()

    @staticmethod
    def _risk_band(
        probability: float,
    ) -> str:

        if probability >= 0.70:
            return "Critical"
        if probability >= 0.50:
            return "High"
        if probability >= 0.30:
            return "Elevated"
        if probability >= 0.15:
            return "Guarded"
        return "Low"

    @staticmethod
    def _markov_escalation_probability(
        markov: dict[str, Any],
    ) -> float:

        distribution = (
            markov.get(
                "forecast_distribution"
            )
            or {}
        )

        return (
            float(
                distribution.get(
                    "S3_LIMITED_CONFLICT",
                    0.0,
                )
            )
            + float(
                distribution.get(
                    "S4_WAR",
                    0.0,
                )
            )
        )

    @staticmethod
    def _normalize_weights(
        weights: dict[str, float],
    ) -> dict[str, float]:

        total = sum(
            weights.values()
        )

        if total <= 0:
            raise ValueError(
                "No applicable ensemble models."
            )

        return {
            key: value / total
            for key, value
            in weights.items()
        }

    def forecast(
        self,
        conflict_id: int,
        horizon_days: int = 30,
        lookback_days: int = 30,
    ) -> dict[str, Any]:

        markov = self.markov.forecast(
            conflict_id,
            horizon_days,
        )

        preconflict = self.preconflict.forecast(
            conflict_id,
            horizon_days,
            lookback_days,
        )

        dyadic = self.dyadic.forecast(
            conflict_id,
            horizon_days,
            lookback_days,
        )

        frozen = self.frozen.forecast(
            conflict_id,
            horizon_days,
            lookback_days,
        )

        current_state = str(
            markov[
                "current_state"
            ]
        )

        markov_probability = (
            self._markov_escalation_probability(
                markov
            )
        )

        preconflict_probability = float(
            preconflict[
                "armed_conflict_onset_probability"
            ]
        )

        dyadic_probability = float(
            dyadic[
                "dyadic_escalation_probability"
            ]
        )

        frozen_probability = float(
            frozen[
                "reactivation_probability"
            ]
        )

        frozen_match = (
            frozen.get(
                "frozen_conflict_match"
            )
            is not None
        )

        markov_applicable = (
            current_state
            in UCDP_MARKOV_STATES
        )

        # Base model importance before applicability filtering.
        weights = {
            "preconflict": 0.35,
            "dyadic": 0.40,
        }

        if markov_applicable:
            weights[
                "markov"
            ] = 0.25

        if frozen_match:
            weights[
                "frozen"
            ] = 0.30

        weights = (
            self._normalize_weights(
                weights
            )
        )

        components = {
            "markov":
                markov_probability,

            "preconflict":
                preconflict_probability,

            "dyadic":
                dyadic_probability,

            "frozen":
                frozen_probability,
        }

        probability = sum(
            weights[name]
            * components[name]
            for name in weights
        )

        probability = min(
            max(
                probability,
                0.0,
            ),
            0.99,
        )

        confidence_values = [
            float(
                markov.get(
                    "current_confidence"
                )
                or 0
            ),
            float(
                preconflict.get(
                    "current_state_confidence"
                )
                or 0
            ),
        ]

        confidence_values = [
            value
            for value in confidence_values
            if value > 0
        ]

        confidence = (
            sum(
                confidence_values
            )
            / len(
                confidence_values
            )
            if confidence_values
            else 0.0
        )

        return {
            "conflict_id":
                conflict_id,

            "canonical_episode_id":
                markov[
                    "canonical_episode_id"
                ],

            "current_state":
                current_state,

            "horizon_days":
                horizon_days,

            "lookback_days":
                lookback_days,

            "ensemble_probability":
                round(
                    probability,
                    6,
                ),

            "risk_band":
                self._risk_band(
                    probability
                ),

            "confidence":
                round(
                    confidence,
                    1,
                ),

            "component_probabilities": {
                "markov_escalation":
                    round(
                        markov_probability,
                        6,
                    ),

                "preconflict_onset":
                    round(
                        preconflict_probability,
                        6,
                    ),

                "dyadic_escalation":
                    round(
                        dyadic_probability,
                        6,
                    ),

                "frozen_reactivation":
                    round(
                        frozen_probability,
                        6,
                    ),
            },

            "model_applicability": {
                "markov":
                    markov_applicable,

                "preconflict":
                    True,

                "dyadic":
                    True,

                "frozen":
                    frozen_match,
            },

            "normalized_weights": {
                key: round(
                    value,
                    6,
                )
                for key, value
                in weights.items()
            },

            "frozen_conflict_match":
                frozen.get(
                    "frozen_conflict_match"
                ),

            "state_forecast_distribution":
                markov.get(
                    "forecast_distribution"
                ),

            "primary_evidence":
                preconflict.get(
                    "primary_evidence"
                )
                or [],

            "models": {
                "markov":
                    markov.get(
                        "model"
                    ),

                "preconflict":
                    preconflict.get(
                        "model"
                    ),

                "dyadic":
                    dyadic.get(
                        "model"
                    ),

                "frozen":
                    frozen.get(
                        "model"
                    ),
            },

            "ensemble_model":
                "conflict-ensemble-v1",
        }
