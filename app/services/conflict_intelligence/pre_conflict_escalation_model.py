from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)


MATRIX_VERSION = "conflict-transition-matrix-v2"

EVENT_WEIGHTS = {
    "military_activity": 0.55,
    "military_mobilization": 0.85,
    "border_incident": 0.75,
    "armed_clash": 1.20,
    "airstrike": 1.35,
    "missile_strike": 1.45,
    "invasion": 2.00,
    "ceasefire_violation": 0.90,
    "diplomatic_breakdown": 0.65,
    "sanctions": 0.25,
    "protest": 0.15,
    "ceasefire": -0.70,
    "peace_agreement": -1.20,
    "withdrawal": -0.55,
}


class PreConflictEscalationModel:

    def __init__(self) -> None:
        self.db = get_supabase_client()

    @staticmethod
    def _logit(p: float) -> float:
        p = min(
            max(p, 0.000001),
            0.999999,
        )
        return math.log(
            p / (1.0 - p)
        )

    @staticmethod
    def _sigmoid(x: float) -> float:
        return 1.0 / (
            1.0 + math.exp(-x)
        )

    def _annual_onset_prior(
        self,
    ) -> float:

        rows = (
            self.db.table(
                "conflict_state_transitions"
            )
            .select(
                "to_state,probability"
            )
            .eq(
                "matrix_version",
                MATRIX_VERSION,
            )
            .eq(
                "from_state",
                "S0_STABLE",
            )
            .eq(
                "active",
                True,
            )
            .execute()
            .data
            or []
        )

        # Armed-conflict onset means entering
        # S3 limited conflict or S4 war.
        onset = 0.0

        for row in rows:
            if row["to_state"] in {
                "S3_LIMITED_CONFLICT",
                "S4_WAR",
            }:
                onset += float(
                    row["probability"]
                )

        return min(
            max(onset, 0.0001),
            0.9999,
        )

    @staticmethod
    def _horizon_prior(
        annual_probability: float,
        horizon_days: int,
    ) -> float:

        fraction = (
            horizon_days / 365.0
        )

        return 1.0 - (
            (1.0 - annual_probability)
            ** fraction
        )

    def _observations(
        self,
        conflict_id: int,
        lookback_days: int,
    ) -> list[dict[str, Any]]:

        since = (
            datetime.now(timezone.utc)
            - timedelta(
                days=lookback_days
            )
        ).isoformat()

        return (
            self.db.table(
                "conflict_observations"
            )
            .select(
                "observation_key,"
                "observed_at,"
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
            .order(
                "observed_at",
                desc=True,
            )
            .execute()
            .data
            or []
        )

    @staticmethod
    def _confidence_factor(
        grade: str | None,
    ) -> float:

        return {
            "high": 1.00,
            "medium": 0.75,
            "low": 0.50,
            "unknown": 0.35,
        }.get(
            str(
                grade or "unknown"
            ).lower(),
            0.35,
        )

    def _evidence_score(
        self,
        observations: list[dict[str, Any]],
    ) -> tuple[
        float,
        list[dict[str, Any]],
    ]:

        if not observations:
            return 0.0, []

        score = 0.0
        drivers = []

        for row in observations:

            event_type = str(
                row.get("event_type")
                or "unknown"
            ).lower()

            severity = float(
                row.get("severity")
                or 0
            )

            confidence = (
                self._confidence_factor(
                    row.get(
                        "confidence_grade"
                    )
                )
            )

            weight = EVENT_WEIGHTS.get(
                event_type,
                0.20,
            )

            contribution = (
                weight
                * (
                    severity / 100.0
                )
                * confidence
            )

            score += contribution

            drivers.append(
                {
                    "observation_key":
                        row.get(
                            "observation_key"
                        ),

                    "event_type":
                        event_type,

                    "severity":
                        severity,

                    "contribution":
                        round(
                            contribution,
                            4,
                        ),
                }
            )

        drivers.sort(
            key=lambda item:
                abs(
                    item[
                        "contribution"
                    ]
                ),
            reverse=True,
        )

        # Prevent one noisy collection window
        # from dominating the prior.
        score = min(
            max(score, -3.0),
            3.0,
        )

        return (
            score,
            drivers[:10],
        )

    def forecast(
        self,
        conflict_id: int,
        horizon_days: int = 30,
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

        current_rows = (
            self.db.table(
                "conflict_current_state"
            )
            .select(
                "state_code,"
                "confidence,"
                "canonical_episode_id"
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

        if not current_rows:
            raise ValueError(
                f"No current state found for "
                f"conflict_id {conflict_id}"
            )

        current = current_rows[0]

        observations = (
            self._observations(
                conflict_id,
                lookback_days,
            )
        )

        annual_prior = (
            self._annual_onset_prior()
        )

        horizon_prior = (
            self._horizon_prior(
                annual_prior,
                horizon_days,
            )
        )

        (
            evidence_score,
            drivers,
        ) = self._evidence_score(
            observations
        )

        posterior_log_odds = (
            self._logit(
                horizon_prior
            )
            + evidence_score
        )

        probability = (
            self._sigmoid(
                posterior_log_odds
            )
        )

        if probability >= 0.65:
            risk_band = "High"
        elif probability >= 0.40:
            risk_band = "Elevated"
        elif probability >= 0.20:
            risk_band = "Guarded"
        else:
            risk_band = "Low"

        return {
            "conflict_id":
                conflict_id,

            "canonical_episode_id":
                current[
                    "canonical_episode_id"
                ],

            "current_state":
                current[
                    "state_code"
                ],

            "horizon_days":
                horizon_days,

            "lookback_days":
                lookback_days,

            "annual_armed_conflict_onset_prior":
                round(
                    annual_prior,
                    6,
                ),

            "horizon_prior_probability":
                round(
                    horizon_prior,
                    6,
                ),

            "evidence_log_odds_adjustment":
                round(
                    evidence_score,
                    6,
                ),

            "armed_conflict_onset_probability":
                round(
                    probability,
                    6,
                ),

            "risk_band":
                risk_band,

            "observation_count":
                len(
                    observations
                ),

            "primary_evidence":
                drivers,

            "current_state_confidence":
                float(
                    current[
                        "confidence"
                    ]
                ),

            "model":
                "pre-conflict-bayesian-logit-v1",

            "historical_prior_source":
                MATRIX_VERSION,

            "target_event":
                "entry_into_S3_or_S4",
        }
