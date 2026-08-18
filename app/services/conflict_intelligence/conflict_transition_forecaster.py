from __future__ import annotations

from typing import Any

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)


STATE_ORDER = [
    "S0_STABLE",
    "S1_TENSION",
    "S2_CRISIS",
    "S3_LIMITED_CONFLICT",
    "S4_WAR",
    "S5_FROZEN",
]

SUPPORTED_HORIZONS = [
    30,
    90,
    180,
    365,
]

TRANSITION_MATRIX_VERSION = (
    "conflict-transition-matrix-v1"
)


class ConflictTransitionForecaster:

    def __init__(self) -> None:
        self.db = get_supabase_client()

    def _current_state(
        self,
        conflict_id: int,
    ) -> dict[str, Any]:

        rows = (
            self.db.table(
                "conflict_current_state"
            )
            .select(
                "conflict_id,"
                "canonical_episode_id,"
                "state_code,"
                "escalation_probability,"
                "confidence,"
                "calculated_at"
            )
            .eq(
                "conflict_id",
                conflict_id,
            )
            .limit(1)
            .execute()
            .data
            or []
        )

        if not rows:
            raise ValueError(
                f"No current state found for conflict_id {conflict_id}"
            )

        return rows[0]

    def _annual_matrix(
        self,
    ) -> dict[str, dict[str, float]]:

        rows = (
            self.db.table(
                "conflict_state_transitions"
            )
            .select(
                "from_state,"
                "to_state,"
                "probability"
            )
            .eq(
                "active",
                True,
            )
            .eq(
                "matrix_version",
                TRANSITION_MATRIX_VERSION,
            )
            .execute()
            .data
            or []
        )

        matrix = {
            state: {
                target: 0.0
                for target in STATE_ORDER
            }
            for state in STATE_ORDER
        }

        for row in rows:

            from_state = str(
                row["from_state"]
            )

            to_state = str(
                row["to_state"]
            )

            if (
                from_state not in matrix
                or to_state not in matrix[from_state]
            ):
                continue

            matrix[from_state][to_state] = float(
                row["probability"]
            )

        for state in STATE_ORDER:

            total = sum(
                matrix[state].values()
            )

            if total <= 0:
                matrix[state][state] = 1.0
                continue

            matrix[state] = {
                target: value / total
                for target, value
                in matrix[state].items()
            }

        return matrix

    @staticmethod
    def _annual_fraction(
        horizon_days: int,
    ) -> float:

        return min(
            max(
                horizon_days / 365.0,
                0.0,
            ),
            1.0,
        )

    def _distribution(
        self,
        current_state: str,
        horizon_days: int,
    ) -> dict[str, float]:

        matrix = self._annual_matrix()

        alpha = self._annual_fraction(
            horizon_days
        )

        annual_row = matrix[
            current_state
        ]

        # Transparent annual-to-subannual interpolation:
        #
        # P(t) = (1-alpha)I + alpha P(1 year)
        #
        # This keeps the empirical annual matrix intact while
        # avoiding the incorrect assumption that one annual
        # transition step represents one month.

        distribution = {}

        for target in STATE_ORDER:

            identity = (
                1.0
                if target == current_state
                else 0.0
            )

            probability = (
                (1.0 - alpha) * identity
                + alpha * annual_row[target]
            )

            distribution[target] = probability

        total = sum(
            distribution.values()
        )

        if total > 0:
            distribution = {
                state: value / total
                for state, value
                in distribution.items()
            }

        return {
            state: round(
                probability,
                6,
            )
            for state, probability
            in distribution.items()
        }

    @staticmethod
    def _most_likely_state(
        distribution: dict[str, float],
    ) -> str:

        return max(
            distribution,
            key=distribution.get,
        )

    def forecast(
        self,
        conflict_id: int,
        horizon_days: int = 30,
    ) -> dict[str, Any]:

        if horizon_days not in SUPPORTED_HORIZONS:
            raise ValueError(
                "Supported horizons are "
                "30, 90, 180, and 365 days."
            )

        current = self._current_state(
            conflict_id
        )

        current_state = str(
            current["state_code"]
        )

        distribution = self._distribution(
            current_state,
            horizon_days,
        )

        return {
            "conflict_id":
                conflict_id,

            "canonical_episode_id":
                current[
                    "canonical_episode_id"
                ],

            "current_state":
                current_state,

            "forecast_horizon_days":
                horizon_days,

            "horizon_year_fraction":
                round(
                    self._annual_fraction(
                        horizon_days
                    ),
                    6,
                ),

            "forecast_distribution":
                distribution,

            "most_likely_state":
                self._most_likely_state(
                    distribution
                ),

            "current_escalation_probability":
                float(
                    current[
                        "escalation_probability"
                    ]
                ),

            "current_confidence":
                float(
                    current[
                        "confidence"
                    ]
                ),

            "model":
                "empirical-annual-markov-v3",

            "source_matrix":
                TRANSITION_MATRIX_VERSION,

            "transition_timebase":
                "annual",
        }

    def forecast_all_horizons(
        self,
        conflict_id: int,
    ) -> dict[str, Any]:

        current = self._current_state(
            conflict_id
        )

        current_state = str(
            current["state_code"]
        )

        forecasts = {}

        for horizon_days in SUPPORTED_HORIZONS:

            distribution = self._distribution(
                current_state,
                horizon_days,
            )

            forecasts[
                str(horizon_days)
            ] = {
                "horizon_days":
                    horizon_days,

                "horizon_year_fraction":
                    round(
                        self._annual_fraction(
                            horizon_days
                        ),
                        6,
                    ),

                "distribution":
                    distribution,

                "most_likely_state":
                    self._most_likely_state(
                        distribution
                    ),
            }

        return {
            "conflict_id":
                conflict_id,

            "canonical_episode_id":
                current[
                    "canonical_episode_id"
                ],

            "current_state":
                current_state,

            "current_escalation_probability":
                float(
                    current[
                        "escalation_probability"
                    ]
                ),

            "current_confidence":
                float(
                    current[
                        "confidence"
                    ]
                ),

            "forecasts":
                forecasts,

            "model":
                "empirical-annual-markov-v3",

            "source_matrix":
                TRANSITION_MATRIX_VERSION,

            "transition_timebase":
                "annual",
        }
