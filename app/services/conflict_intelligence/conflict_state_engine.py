from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)


STATE_ORDER = {
    "S0_STABLE": 0,
    "S1_TENSION": 1,
    "S2_CRISIS": 2,
    "S3_LIMITED_CONFLICT": 3,
    "S4_WAR": 4,
    "S5_FROZEN": 5,
}


EVENT_WEIGHTS = {
    "military_activity": 1.00,
    "military_mobilization": 1.15,
    "border_incident": 1.10,
    "armed_clash": 1.35,
    "airstrike": 1.40,
    "missile_strike": 1.45,
    "invasion": 1.60,
    "ceasefire_violation": 1.20,
    "diplomatic_breakdown": 0.90,
    "sanctions": 0.60,
    "protest": 0.45,
    "election": 0.20,
    "ceasefire": -0.80,
    "peace_agreement": -1.20,
    "withdrawal": -0.70,
}


class ConflictStateEngine:

    def __init__(self):
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
                "id,conflict_id,"
                "start_year,end_year,"
                "peak_intensity,"
                "state_participants"
            )
            .eq("conflict_id", conflict_id)
            .limit(1)
            .execute()
            .data
            or []
        )

        if not rows:
            raise ValueError(
                f"Unknown conflict_id: {conflict_id}"
            )

        return rows[0]

    def _observations(
        self,
        conflict_id: int,
        window_days: int = 30,
    ) -> list[dict[str, Any]]:

        since = (
            datetime.now(timezone.utc)
            - timedelta(days=window_days)
        ).isoformat()

        return (
            self.db.table("conflict_observations")
            .select(
                "observation_key,"
                "observed_at,"
                "event_type,"
                "severity,"
                "confidence_grade"
            )
            .eq("conflict_id", conflict_id)
            .eq("active", True)
            .gte("observed_at", since)
            .order("observed_at")
            .execute()
            .data
            or []
        )

    @staticmethod
    def _confidence_value(
        grade: str | None,
    ) -> float:

        return {
            "high": 90.0,
            "medium": 70.0,
            "low": 45.0,
            "unknown": 25.0,
        }.get(
            str(grade or "unknown").lower(),
            25.0,
        )

    def _score(
        self,
        observations: list[dict[str, Any]],
    ) -> tuple[
        float,
        float,
        int,
        float,
        list[str],
        list[str],
    ]:

        if not observations:
            return (
                0.05,
                20.0,
                0,
                0.0,
                [],
                [],
            )

        weighted_total = 0.0
        severities = []
        confidences = []
        event_counter = Counter()
        observation_keys = []

        for row in observations:

            event_type = str(
                row.get("event_type")
                or "unknown"
            ).lower()

            severity = float(
                row.get("severity")
                or 0
            )

            weight = EVENT_WEIGHTS.get(
                event_type,
                0.50,
            )

            weighted_total += (
                severity / 100.0
            ) * weight

            severities.append(severity)

            confidences.append(
                self._confidence_value(
                    row.get("confidence_grade")
                )
            )

            event_counter[event_type] += 1

            if row.get("observation_key"):
                observation_keys.append(
                    row["observation_key"]
                )

        n = len(observations)

        mean_severity = (
            sum(severities) / n
        )

        max_severity = int(
            max(severities)
        )

        signal_density = min(
            n / 10.0,
            1.0,
        )

        raw_probability = (
            0.10
            + 0.50 * min(
                weighted_total / 5.0,
                1.0,
            )
            + 0.25 * (
                mean_severity / 100.0
            )
            + 0.15 * signal_density
        )

        probability = max(
            0.01,
            min(raw_probability, 0.99),
        )

        confidence = min(
            95.0,
            (
                sum(confidences)
                / len(confidences)
            )
            * (
                0.65
                + 0.35 * signal_density
            ),
        )

        drivers = [
            event
            for event, _
            in event_counter.most_common(5)
        ]

        return (
            probability,
            confidence,
            max_severity,
            mean_severity,
            drivers,
            observation_keys[-25:],
        )

    @staticmethod
    def _state(
        probability: float,
        severity_max: int,
    ) -> str:

        if (
            probability >= 0.80
            or severity_max >= 90
        ):
            return "S4_WAR"

        if (
            probability >= 0.60
            or severity_max >= 75
        ):
            return "S3_LIMITED_CONFLICT"

        if (
            probability >= 0.40
            or severity_max >= 60
        ):
            return "S2_CRISIS"

        if (
            probability >= 0.20
            or severity_max >= 35
        ):
            return "S1_TENSION"

        return "S0_STABLE"

    @staticmethod
    def _direction(
        previous_state: str | None,
        current_state: str,
    ) -> str:

        if not previous_state:
            return "stable"

        previous = STATE_ORDER.get(
            previous_state,
            0,
        )

        current = STATE_ORDER.get(
            current_state,
            0,
        )

        if current > previous:
            return "deteriorating"

        if current < previous:
            return "improving"

        return "stable"

    def _transition_probabilities(
        self,
        state_code: str,
    ) -> dict[str, float]:

        rows = (
            self.db.table(
                "conflict_state_transitions"
            )
            .select(
                "to_state,probability"
            )
            .eq(
                "from_state",
                state_code,
            )
            .eq(
                "active",
                True,
            )
            .order(
                "probability",
                desc=True,
            )
            .execute()
            .data
            or []
        )

        return {
            str(row["to_state"]):
                float(row["probability"])
            for row in rows
        }

    def assess(
        self,
        conflict_id: int,
        window_days: int = 30,
    ) -> dict[str, Any]:

        episode = self._episode(
            conflict_id
        )

        observations = self._observations(
            conflict_id,
            window_days,
        )

        (
            probability,
            confidence,
            severity_max,
            severity_mean,
            drivers,
            observation_keys,
        ) = self._score(
            observations
        )

        current_state = self._state(
            probability,
            severity_max,
        )

        previous_rows = (
            self.db.table(
                "conflict_current_state"
            )
            .select(
                "state_code,"
                "escalation_probability"
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

        previous_state = (
            previous_rows[0]["state_code"]
            if previous_rows
            else None
        )

        direction = self._direction(
            previous_state,
            current_state,
        )

        now = datetime.now(
            timezone.utc
        ).isoformat()

        transition_probabilities = (
            self._transition_probabilities(
                current_state
            )
        )

        row = {
            "conflict_id":
                conflict_id,

            "canonical_episode_id":
                episode["id"],

            "state_code":
                current_state,

            "previous_state_code":
                previous_state,

            "direction":
                direction,

            "escalation_probability":
                round(probability, 4),

            "confidence":
                round(confidence, 1),

            "observation_count":
                len(observations),

            "severity_mean":
                round(severity_mean, 2),

            "severity_max":
                severity_max,

            "primary_drivers":
                drivers,

            "supporting_observation_keys":
                observation_keys,

            "formula_version":
                "conflict-state-v1",

            "calculated_at":
                now,

            "updated_at":
                now,
        }

        (
            self.db.table(
                "conflict_current_state"
            )
            .upsert(
                row,
                on_conflict="conflict_id",
            )
            .execute()
        )

        history_row = {
            **row,

            # Legacy compatibility fields
            "unit_id": str(conflict_id),
            "unit_type": "episode",
            "observed_at": now,

            # Preserve the legacy state column while also
            # storing the new state_code field.
            "conflict_state": current_state,

            "severity_tier": (
                "Critical"
                if severity_max >= 90
                else "High"
                if severity_max >= 75
                else "Elevated"
                if severity_max >= 60
                else "Guarded"
                if severity_max >= 35
                else "Minimal"
            ),

            "source": "conflict-state-engine",
            "source_version": "conflict-state-v1",

            "evidence_refs": observation_keys,
        }

        history_row.pop(
            "updated_at",
            None,
        )

        (
            self.db.table(
                "conflict_state_history"
            )
            .insert(
                history_row
            )
            .execute()
        )

        return {
            **row,
            "transition_probabilities":
                transition_probabilities,
        }
