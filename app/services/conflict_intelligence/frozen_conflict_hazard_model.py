from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)

from app.services.conflict_intelligence.pre_conflict_escalation_model import (
    PreConflictEscalationModel,
)


class FrozenConflictHazardModel:

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
                "end_year"
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

    def _frozen_conflict(
        self,
        states: list[str],
        conflict_id: int | None = None,
    ) -> dict[str, Any] | None:

        frozen_rows = (
            self.db.table(
                "conflict_frozen_conflicts"
            )
            .select("*")
            .eq(
                "active",
                True,
            )
            .execute()
            .data
            or []
        )

        target_states = sorted(
            {
                str(x).strip().upper()
                for x in states
                if x
            }
        )

        # 1. Exact dyad match is the strongest linkage.
        if len(target_states) == 2:

            dyad_id = (
                "DYAD-"
                + "-".join(
                    target_states
                )
                + "-LAND"
            )

            for row in frozen_rows:
                if (
                    row.get(
                        "primary_dyad_id"
                    )
                    == dyad_id
                ):
                    return row

        # 2. Resolve through the dispute registry.
        dispute_rows = (
            self.db.table(
                "conflict_disputes"
            )
            .select(
                "dispute_id,"
                "claimant_iso3,"
                "primary_dyad_id,"
                "territory_id,"
                "parties"
            )
            .eq(
                "active",
                True,
            )
            .execute()
            .data
            or []
        )

        matching_dispute_ids = set()
        matching_dyads = set()
        matching_territories = set()

        target_set = set(
            target_states
        )

        for dispute in dispute_rows:

            claimants = {
                str(x).strip().upper()
                for x in (
                    dispute.get(
                        "claimant_iso3"
                    )
                    or []
                )
                if x
            }

            if (
                target_set
                and claimants
                and target_set.issubset(
                    claimants
                )
            ):
                if dispute.get(
                    "dispute_id"
                ):
                    matching_dispute_ids.add(
                        dispute[
                            "dispute_id"
                        ]
                    )

                if dispute.get(
                    "primary_dyad_id"
                ):
                    matching_dyads.add(
                        dispute[
                            "primary_dyad_id"
                        ]
                    )

                if dispute.get(
                    "territory_id"
                ):
                    matching_territories.add(
                        dispute[
                            "territory_id"
                        ]
                    )

        for row in frozen_rows:

            if (
                row.get(
                    "dispute_id"
                )
                in matching_dispute_ids
            ):
                return row

            if (
                row.get(
                    "primary_dyad_id"
                )
                in matching_dyads
            ):
                return row

            if (
                row.get(
                    "territory_id"
                )
                in matching_territories
            ):
                return row

        return None

    def _historical_recurrence(
        self,
        conflict_id: int,
    ) -> dict[str, Any]:

        rows = (
            self.db.table(
                "conflict_state_timeline"
            )
            .select(
                "year,state_code"
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

        armed = {
            "S3_LIMITED_CONFLICT",
            "S4_WAR",
        }

        recurrence_events = 0
        armed_years = 0
        stable_years = 0
        previous_armed = False

        for row in rows:

            current_armed = (
                row["state_code"]
                in armed
            )

            if current_armed:
                armed_years += 1
            else:
                stable_years += 1

            if (
                current_armed
                and not previous_armed
            ):
                recurrence_events += 1

            previous_armed = (
                current_armed
            )

        years = max(
            len(rows),
            1,
        )

        return {
            "timeline_years":
                years,

            "armed_years":
                armed_years,

            "stable_years":
                stable_years,

            "recurrence_events":
                recurrence_events,

            "armed_share":
                round(
                    armed_years
                    / years,
                    6,
                ),
        }

    @staticmethod
    def _duration_factor(
        end_year: int | None,
    ) -> float:

        if not end_year:
            return 0.5

        years_since = max(
            datetime.now(
                timezone.utc
            ).year
            - int(end_year),
            0,
        )

        # Decays gradually rather than sharply.
        return math.exp(
            -years_since / 20.0
        )

    def forecast(
        self,
        conflict_id: int,
        horizon_days: int = 365,
        lookback_days: int = 30,
    ) -> dict[str, Any]:

        if horizon_days not in {
            30,
            90,
            180,
            365,
        }:
            raise ValueError(
                "Supported horizons are "
                "30, 90, 180, and 365 days."
            )

        episode = self._episode(
            conflict_id
        )

        states = (
            episode.get(
                "state_participants"
            )
            or []
        )

        frozen = (
            self._frozen_conflict(
                states,
                conflict_id,
            )
        )

        recurrence = (
            self._historical_recurrence(
                conflict_id
            )
        )

        # Build the frozen-conflict hazard on an annual
        # timebase, then convert it to the requested horizon.
        annual_base = (
            PreConflictEscalationModel()
            .forecast(
                conflict_id,
                365,
                lookback_days,
            )
        )

        recurrence_pressure = min(
            (
                recurrence[
                    "recurrence_events"
                ] / 8.0
            ),
            1.0,
        )

        armed_share = float(
            recurrence[
                "armed_share"
            ]
        )

        duration_factor = (
            self._duration_factor(
                episode.get(
                    "end_year"
                )
            )
        )

        frozen_bonus = (
            0.20
            if frozen
            else 0.0
        )

        annual_probability = (
            0.50
            * float(
                annual_base[
                    "armed_conflict_onset_probability"
                ]
            )
            + 0.20
            * recurrence_pressure
            + 0.15
            * armed_share
            + 0.15
            * duration_factor
            + frozen_bonus
        )

        annual_probability = min(
            max(
                annual_probability,
                0.000001,
            ),
            0.99,
        )

        horizon_fraction = (
            horizon_days / 365.0
        )

        probability = (
            1.0
            - (
                1.0
                - annual_probability
            ) ** horizon_fraction
        )

        if probability >= 0.60:
            risk_band = "High"
        elif probability >= 0.35:
            risk_band = "Elevated"
        elif probability >= 0.15:
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

            "frozen_conflict_match":
                frozen,

            "horizon_days":
                horizon_days,

            "lookback_days":
                lookback_days,

            "base_onset_probability":
                annual_base[
                    "armed_conflict_onset_probability"
                ],

            "annual_reactivation_probability":
                round(
                    annual_probability,
                    6,
                ),

            "recurrence_pressure":
                round(
                    recurrence_pressure,
                    6,
                ),

            "armed_share":
                round(
                    armed_share,
                    6,
                ),

            "duration_factor":
                round(
                    duration_factor,
                    6,
                ),

            "frozen_conflict_bonus":
                frozen_bonus,

            "reactivation_probability":
                round(
                    probability,
                    6,
                ),

            "risk_band":
                risk_band,

            "historical_recurrence":
                recurrence,

            "model":
                "frozen-conflict-hazard-v1",
        }
