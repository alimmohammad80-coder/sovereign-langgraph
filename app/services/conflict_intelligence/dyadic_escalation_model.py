from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)

from app.services.conflict_intelligence.pre_conflict_escalation_model import (
    PreConflictEscalationModel,
)


class DyadicEscalationModel:

    def __init__(self) -> None:
        self.db = get_supabase_client()

    def _episode(
        self,
        conflict_id: int,
    ) -> dict[str, Any]:

        rows = (
            self.db.table(
                "conflict_canonical_episodes"
            )
            .select(
                "id,"
                "conflict_id,"
                "state_participants,"
                "start_year,"
                "end_year,"
                "peak_intensity"
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
                f"Unknown conflict_id {conflict_id}"
            )

        return rows[0]

    def _dyad(
        self,
        states: list[str],
    ) -> dict[str, Any] | None:

        if len(states) != 2:
            return None

        a, b = sorted(
            {
                str(x).strip().upper()
                for x in states
                if x
            }
        )

        dyad_key = (
            f"DYAD-{a}-{b}-LAND"
        )

        rows = (
            self.db.table(
                "conflict_border_dyads"
            )
            .select("*")
            .eq(
                "dyad_id",
                dyad_key,
            )
            .limit(1)
            .execute()
            .data
            or []
        )

        if rows:
            return rows[0]

        return {
            "dyad_id":
                dyad_key,

            "state_a":
                a,

            "state_b":
                b,

            "synthetic":
                True,
        }

    def _historical_metrics(
        self,
        conflict_id: int,
    ) -> dict[str, Any]:

        rows = (
            self.db.table(
                "conflict_state_timeline"
            )
            .select(
                "year,"
                "state_code"
            )
            .eq(
                "conflict_id",
                conflict_id,
            )
            .eq(
                "active",
                True,
            )
            .order(
                "year"
            )
            .execute()
            .data
            or []
        )

        war_years = 0
        limited_conflict_years = 0
        stable_years = 0
        escalations = 0

        previous_state = None

        rank = {
            "S0_STABLE": 0,
            "S1_TENSION": 1,
            "S2_CRISIS": 2,
            "S3_LIMITED_CONFLICT": 3,
            "S4_WAR": 4,
            "S5_FROZEN": 1,
        }

        for row in rows:

            state = str(
                row["state_code"]
            )

            if state == "S4_WAR":
                war_years += 1

            elif state == "S3_LIMITED_CONFLICT":
                limited_conflict_years += 1

            elif state == "S0_STABLE":
                stable_years += 1

            if (
                previous_state is not None
                and rank.get(state, 0)
                > rank.get(
                    previous_state,
                    0,
                )
            ):
                escalations += 1

            previous_state = state

        return {
            "timeline_years":
                len(rows),

            "war_years":
                war_years,

            "limited_conflict_years":
                limited_conflict_years,

            "stable_years":
                stable_years,

            "historical_escalations":
                escalations,
        }

    def _recent_observation_metrics(
        self,
        conflict_id: int,
        lookback_days: int,
    ) -> dict[str, Any]:

        since = (
            datetime.now(
                timezone.utc
            )
            - timedelta(
                days=lookback_days
            )
        ).isoformat()

        rows = (
            self.db.table(
                "conflict_observations"
            )
            .select(
                "event_type,"
                "severity,"
                "confidence_grade"
            )
            .eq(
                "conflict_id",
                conflict_id,
            )
            .eq(
                "active",
                True,
            )
            .gte(
                "observed_at",
                since,
            )
            .execute()
            .data
            or []
        )

        severities = [
            float(
                row.get("severity")
                or 0
            )
            for row in rows
        ]

        return {
            "observation_count":
                len(rows),

            "mean_severity":
                round(
                    sum(severities)
                    / len(severities),
                    2,
                )
                if severities
                else 0.0,

            "max_severity":
                max(severities)
                if severities
                else 0.0,
        }

    @staticmethod
    def _historical_pressure(
        metrics: dict[str, Any],
    ) -> float:

        years = max(
            metrics[
                "timeline_years"
            ],
            1,
        )

        armed_share = (
            metrics[
                "war_years"
            ]
            + metrics[
                "limited_conflict_years"
            ]
        ) / years

        recurrence = min(
            metrics[
                "historical_escalations"
            ] / 10.0,
            1.0,
        )

        return min(
            (
                0.70 * armed_share
                + 0.30 * recurrence
            ),
            1.0,
        )

    def forecast(
        self,
        conflict_id: int,
        horizon_days: int = 30,
        lookback_days: int = 30,
    ) -> dict[str, Any]:

        episode = self._episode(
            conflict_id
        )

        states = (
            episode.get(
                "state_participants"
            )
            or []
        )

        dyad = self._dyad(
            states
        )

        historical = (
            self._historical_metrics(
                conflict_id
            )
        )

        recent = (
            self._recent_observation_metrics(
                conflict_id,
                lookback_days,
            )
        )

        base = (
            PreConflictEscalationModel()
            .forecast(
                conflict_id,
                horizon_days,
                lookback_days,
            )
        )

        historical_pressure = (
            self._historical_pressure(
                historical
            )
        )

        observation_pressure = min(
            (
                recent[
                    "mean_severity"
                ] / 100.0
            )
            * min(
                recent[
                    "observation_count"
                ] / 5.0,
                1.0,
            ),
            1.0,
        )

        base_probability = float(
            base[
                "armed_conflict_onset_probability"
            ]
        )

        dyadic_probability = min(
            max(
                (
                    0.65
                    * base_probability
                    + 0.25
                    * historical_pressure
                    + 0.10
                    * observation_pressure
                ),
                0.0,
            ),
            0.99,
        )

        if dyadic_probability >= 0.60:
            risk_band = "High"
        elif dyadic_probability >= 0.35:
            risk_band = "Elevated"
        elif dyadic_probability >= 0.15:
            risk_band = "Guarded"
        else:
            risk_band = "Low"

        return {
            "conflict_id":
                conflict_id,

            "canonical_episode_id":
                episode["id"],

            "state_participants":
                states,

            "dyad":
                dyad,

            "horizon_days":
                horizon_days,

            "lookback_days":
                lookback_days,

            "base_onset_probability":
                round(
                    base_probability,
                    6,
                ),

            "historical_pressure":
                round(
                    historical_pressure,
                    6,
                ),

            "observation_pressure":
                round(
                    observation_pressure,
                    6,
                ),

            "dyadic_escalation_probability":
                round(
                    dyadic_probability,
                    6,
                ),

            "risk_band":
                risk_band,

            "historical_metrics":
                historical,

            "recent_observation_metrics":
                recent,

            "model":
                "dyadic-escalation-v1",
        }
