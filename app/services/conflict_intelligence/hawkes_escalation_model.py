from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)


PARAMETERS_PATH = Path(
    "app/data/conflict_intelligence/hawkes_parameters.json"
)

CLASSIFICATION_PATH = Path(
    "app/data/conflict_intelligence/event_classification.json"
)

SUPPORTED_HORIZONS = {
    30,
    90,
    180,
    365,
}

CONFIDENCE_FACTORS = {
    "high": 1.0,
    "medium": 0.75,
    "low": 0.5,
    "unknown": 0.35,
}


class HawkesEscalationModel:

    def __init__(self) -> None:
        self.db = get_supabase_client()

        self.parameters = json.loads(
            PARAMETERS_PATH.read_text()
        )

        self.classification = json.loads(
            CLASSIFICATION_PATH.read_text()
        )

    @staticmethod
    def _parse_datetime(
        value: str,
    ) -> datetime:

        dt = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt.astimezone(
            timezone.utc
        )

    @staticmethod
    def _confidence_factor(
        grade: str | None,
    ) -> float:

        return CONFIDENCE_FACTORS.get(
            str(
                grade
                or "unknown"
            ).lower(),
            0.35,
        )

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
                "confidence"
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

    def _observations(
        self,
        conflict_id: int,
        lookback_days: int,
    ) -> list[dict[str, Any]]:

        since = (
            datetime.now(
                timezone.utc
            )
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
                "confidence_grade,"
                "source"
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

    def _event_contribution(
        self,
        row: dict[str, Any],
        now: datetime,
    ) -> dict[str, Any]:

        event_type = str(
            row.get(
                "event_type"
            )
            or "unknown"
        ).lower()

        event_class = self.classification.get(
            event_type,
            "routine",
        )

        class_parameters = (
            self.parameters[
                "event_classes"
            ][
                event_class
            ]
        )

        alpha = float(
            class_parameters[
                "alpha"
            ]
        )

        half_life = float(
            class_parameters[
                "half_life_days"
            ]
        )

        beta = (
            math.log(2.0)
            / half_life
        )

        observed_at = (
            self._parse_datetime(
                str(
                    row[
                        "observed_at"
                    ]
                )
            )
        )

        age_days = max(
            (
                now - observed_at
            ).total_seconds()
            / 86400.0,
            0.0,
        )

        severity = min(
            max(
                float(
                    row.get(
                        "severity"
                    )
                    or 0.0
                ),
                0.0,
            ),
            100.0,
        )

        confidence = (
            self._confidence_factor(
                row.get(
                    "confidence_grade"
                )
            )
        )

        decay = math.exp(
            -beta * age_days
        )

        contribution = (
            alpha
            * (
                severity / 100.0
            )
            * confidence
            * decay
        )

        return {
            "observation_key":
                row.get(
                    "observation_key"
                ),

            "event_type":
                event_type,

            "event_class":
                event_class,

            "observed_at":
                row.get(
                    "observed_at"
                ),

            "age_days":
                round(
                    age_days,
                    3,
                ),

            "severity":
                severity,

            "confidence_factor":
                round(
                    confidence,
                    4,
                ),

            "alpha":
                alpha,

            "half_life_days":
                half_life,

            "decay_factor":
                round(
                    decay,
                    6,
                ),

            "contribution":
                round(
                    contribution,
                    6,
                ),

            "source":
                row.get(
                    "source"
                ),
        }

    @staticmethod
    def _burst_density(
        contributions: list[
            dict[str, Any]
        ],
    ) -> float:

        score = 0.0

        for item in contributions:

            age = float(
                item[
                    "age_days"
                ]
            )

            score += (
                math.exp(
                    -age / 7.0
                )
                + 0.5
                * math.exp(
                    -age / 30.0
                )
            )

        return min(
            score / 5.0,
            1.0,
        )

    def _baseline(
        self,
        state_code: str,
    ) -> float:

        return float(
            self.parameters[
                "baseline"
            ].get(
                state_code,
                self.parameters[
                    "baseline"
                ][
                    "S0_STABLE"
                ],
            )
        )

    def _logistic_probability(
        self,
        state_code: str,
        current_intensity: float,
        burst: float,
        event_count: int,
        severity_mean: float,
        horizon_days: int,
    ) -> tuple[
        float,
        float,
    ]:

        params = self.parameters[
            "logistic"
        ]

        horizon_fraction = (
            horizon_days
            / 365.0
        )

        # Recent signal contribution weakens as the
        # requested horizon extends.
        temporal_weight = math.exp(
            -1.5
            * horizon_fraction
        )

        intensity_feature = (
            current_intensity
            * 10.0
            * temporal_weight
        )

        burst_feature = (
            burst
            * temporal_weight
        )

        event_count_feature = min(
            event_count,
            10,
        ) / 10.0

        severity_feature = (
            severity_mean
            / 100.0
        )

        state_offset = float(
            params[
                "state_offsets"
            ].get(
                state_code,
                0.0,
            )
        )

        z = (
            float(
                params[
                    "intercept"
                ]
            )
            + float(
                params[
                    "current_intensity"
                ]
            )
            * intensity_feature
            + float(
                params[
                    "burst"
                ]
            )
            * burst_feature
            + float(
                params[
                    "event_count"
                ]
            )
            * event_count_feature
            + float(
                params[
                    "severity_mean"
                ]
            )
            * severity_feature
            + state_offset
        )

        probability = (
            1.0
            / (
                1.0
                + math.exp(
                    -z
                )
            )
        )

        return (
            probability,
            z,
        )

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

    def forecast(
        self,
        conflict_id: int,
        horizon_days: int = 30,
        lookback_days: int = 90,
    ) -> dict[str, Any]:

        if horizon_days not in SUPPORTED_HORIZONS:
            raise ValueError(
                "Supported horizons are "
                "30, 90, 180, and 365 days."
            )

        current = self._current_state(
            conflict_id
        )

        observations = self._observations(
            conflict_id,
            lookback_days,
        )

        now = datetime.now(
            timezone.utc
        )

        contributions = [
            self._event_contribution(
                row,
                now,
            )
            for row in observations
        ]

        baseline = self._baseline(
            current[
                "state_code"
            ]
        )

        event_intensity = sum(
            float(
                item[
                    "contribution"
                ]
            )
            for item in contributions
        )

        current_intensity = max(
            baseline
            + event_intensity,
            0.0,
        )

        burst = self._burst_density(
            contributions
        )

        severities = [
            float(
                item[
                    "severity"
                ]
            )
            for item in contributions
        ]

        severity_mean = (
            sum(severities)
            / len(severities)
            if severities
            else 0.0
        )

        probability, logit_score = (
            self._logistic_probability(
                current[
                    "state_code"
                ],
                current_intensity,
                burst,
                len(
                    contributions
                ),
                severity_mean,
                horizon_days,
            )
        )

        positive = sorted(
            [
                item
                for item in contributions
                if item[
                    "contribution"
                ] > 0
            ],
            key=lambda item:
                item[
                    "contribution"
                ],
            reverse=True,
        )

        negative = sorted(
            [
                item
                for item in contributions
                if item[
                    "contribution"
                ] < 0
            ],
            key=lambda item:
                item[
                    "contribution"
                ],
        )

        return {
            "conflict_id":
                conflict_id,

            "canonical_episode_id":
                current.get(
                    "canonical_episode_id"
                ),

            "current_state":
                current[
                    "state_code"
                ],

            "horizon_days":
                horizon_days,

            "lookback_days":
                lookback_days,

            "baseline_intensity":
                round(
                    baseline,
                    6,
                ),

            "event_intensity":
                round(
                    event_intensity,
                    6,
                ),

            "current_temporal_intensity":
                round(
                    current_intensity,
                    6,
                ),

            "burst_density":
                round(
                    burst,
                    6,
                ),

            "observation_count":
                len(
                    contributions
                ),

            "severity_mean":
                round(
                    severity_mean,
                    3,
                ),

            "logit_score":
                round(
                    logit_score,
                    6,
                ),

            "temporal_escalation_probability":
                round(
                    probability,
                    6,
                ),

            "risk_band":
                self._risk_band(
                    probability
                ),

            "primary_excitation_events":
                positive[:10],

            "deescalatory_events":
                negative[:10],

            "state_confidence":
                float(
                    current.get(
                        "confidence"
                    )
                    or 0.0
                ),

            "model":
                self.parameters[
                    "model_version"
                ],

            "method":
                "state_baseline_exponential_kernel_logistic",

            "parameters_fitted":
                False,
        }
