from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)


ARMED_STATES = {
    "S3_LIMITED_CONFLICT",
    "S4_WAR",
}


class ConflictForecastOutcomeResolver:

    def __init__(self) -> None:
        self.db = get_supabase_client()

    @staticmethod
    def _maturity_time(
        generated_at: str,
        horizon_days: int,
    ) -> datetime:

        generated = datetime.fromisoformat(
            generated_at.replace(
                "Z",
                "+00:00",
            )
        )

        return (
            generated
            + timedelta(
                days=horizon_days
            )
        )

    def _mature_forecasts(
        self,
        limit: int = 500,
    ) -> list[dict[str, Any]]:

        now = datetime.now(
            timezone.utc
        )

        rows = (
            self.db.table(
                "conflict_forecasts"
            )
            .select(
                "id,"
                "run_key,"
                "conflict_id,"
                "generated_at,"
                "horizon_days,"
                "current_state,"
                "ensemble_probability,"
                "calibrated_probability"
            )
            .is_(
                "outcome_observed_at",
                "null",
            )
            .eq(
                "active",
                True,
            )
            .order(
                "generated_at"
            )
            .limit(
                limit
            )
            .execute()
            .data
            or []
        )

        mature = []

        for row in rows:

            maturity = (
                self._maturity_time(
                    row["generated_at"],
                    int(
                        row["horizon_days"]
                    ),
                )
            )

            if maturity <= now:
                mature.append(
                    {
                        **row,
                        "_maturity_time":
                            maturity,
                    }
                )

        return mature

    def _resolve_state(
        self,
        conflict_id: int,
        maturity_time: datetime,
    ) -> dict[str, Any] | None:

        rows = (
            self.db.table(
                "conflict_state_history"
            )
            .select(
                "state_code,"
                "calculated_at,"
                "observed_at"
            )
            .eq(
                "conflict_id",
                conflict_id,
            )
            .lte(
                "calculated_at",
                maturity_time.isoformat(),
            )
            .order(
                "calculated_at",
                desc=True,
            )
            .limit(1)
            .execute()
            .data
            or []
        )

        if rows:
            return rows[0]

        current = (
            self.db.table(
                "conflict_current_state"
            )
            .select(
                "state_code,"
                "calculated_at"
            )
            .eq(
                "conflict_id",
                conflict_id,
            )
            .lte(
                "calculated_at",
                maturity_time.isoformat(),
            )
            .order(
                "calculated_at",
                desc=True,
            )
            .limit(1)
            .execute()
            .data
            or []
        )

        return (
            current[0]
            if current
            else None
        )

    def resolve(
        self,
        limit: int = 500,
    ) -> dict[str, Any]:

        forecasts = (
            self._mature_forecasts(
                limit
            )
        )

        resolved = 0
        unresolved = 0
        results = []

        for forecast in forecasts:

            maturity_time = forecast[
                "_maturity_time"
            ]

            state = (
                self._resolve_state(
                    int(
                        forecast[
                            "conflict_id"
                        ]
                    ),
                    maturity_time,
                )
            )

            if not state:
                unresolved += 1
                continue

            outcome_state = str(
                state["state_code"]
            )

            event_occurred = (
                outcome_state
                in ARMED_STATES
            )

            outcome_observed_at = (
                state.get(
                    "calculated_at"
                )
                or state.get(
                    "observed_at"
                )
                or maturity_time.isoformat()
            )

            (
                self.db.table(
                    "conflict_forecasts"
                )
                .update(
                    {
                        "outcome_state":
                            outcome_state,

                        "outcome_observed_at":
                            outcome_observed_at,

                        "outcome_event_occurred":
                            event_occurred,

                        "updated_at":
                            datetime.now(
                                timezone.utc
                            ).isoformat(),
                    }
                )
                .eq(
                    "id",
                    forecast["id"],
                )
                .execute()
            )

            resolved += 1

            results.append(
                {
                    "run_key":
                        forecast[
                            "run_key"
                        ],

                    "conflict_id":
                        forecast[
                            "conflict_id"
                        ],

                    "horizon_days":
                        forecast[
                            "horizon_days"
                        ],

                    "outcome_state":
                        outcome_state,

                    "outcome_event_occurred":
                        event_occurred,
                }
            )

        return {
            "checked":
                len(forecasts),

            "resolved":
                resolved,

            "unresolved":
                unresolved,

            "results":
                results,
        }
