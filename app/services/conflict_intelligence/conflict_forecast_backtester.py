from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd


SOURCE = Path(
    "data/processed/conflict_state_timeline.csv"
)

ARMED_STATES = {
    "S3_LIMITED_CONFLICT",
    "S4_WAR",
}


class ConflictForecastBacktester:

    def __init__(self) -> None:
        self.df = pd.read_csv(
            SOURCE,
            dtype=str,
        )

        self.df["conflict_id"] = pd.to_numeric(
            self.df["conflict_id"],
            errors="coerce",
        ).astype("Int64")

        self.df["year"] = pd.to_numeric(
            self.df["year"],
            errors="coerce",
        ).astype("Int64")

        self.df = (
            self.df
            .dropna(
                subset=[
                    "conflict_id",
                    "year",
                    "state_code",
                ]
            )
            .sort_values(
                [
                    "conflict_id",
                    "year",
                ]
            )
        )

    def _transitions(
        self,
        excluded_conflict_id: int,
    ) -> tuple[
        Counter,
        Counter,
    ]:

        counts = Counter()
        totals = Counter()

        training = self.df[
            self.df["conflict_id"]
            != excluded_conflict_id
        ]

        for _, group in training.groupby(
            "conflict_id"
        ):

            group = (
                group
                .sort_values("year")
                .reset_index(drop=True)
            )

            for i in range(
                len(group) - 1
            ):

                current = group.iloc[i]
                following = group.iloc[i + 1]

                if (
                    int(following["year"])
                    != int(current["year"]) + 1
                ):
                    continue

                from_state = str(
                    current["state_code"]
                )

                to_state = str(
                    following["state_code"]
                )

                counts[
                    (
                        from_state,
                        to_state,
                    )
                ] += 1

                totals[
                    from_state
                ] += 1

        return (
            counts,
            totals,
        )

    @staticmethod
    def _armed_probability(
        from_state: str,
        counts: Counter,
        totals: Counter,
    ) -> float:

        denominator = totals[
            from_state
        ]

        if denominator <= 0:
            return 0.0

        numerator = sum(
            counts[
                (
                    from_state,
                    target,
                )
            ]
            for target in ARMED_STATES
        )

        return (
            numerator
            / denominator
        )

    def run(
        self,
    ) -> dict[str, Any]:

        predictions = []

        for conflict_id, group in self.df.groupby(
            "conflict_id"
        ):

            conflict_id = int(
                conflict_id
            )

            counts, totals = (
                self._transitions(
                    conflict_id
                )
            )

            group = (
                group
                .sort_values("year")
                .reset_index(drop=True)
            )

            for i in range(
                len(group) - 1
            ):

                current = group.iloc[i]
                following = group.iloc[i + 1]

                if (
                    int(following["year"])
                    != int(current["year"]) + 1
                ):
                    continue

                current_state = str(
                    current["state_code"]
                )

                next_state = str(
                    following["state_code"]
                )

                # Calibration target:
                # onset from a historically stable state.
                if current_state != "S0_STABLE":
                    continue

                probability = (
                    self._armed_probability(
                        current_state,
                        counts,
                        totals,
                    )
                )

                outcome = (
                    1
                    if next_state
                    in ARMED_STATES
                    else 0
                )

                predictions.append(
                    {
                        "conflict_id":
                            conflict_id,

                        "year":
                            int(
                                current[
                                    "year"
                                ]
                            ),

                        "next_year":
                            int(
                                following[
                                    "year"
                                ]
                            ),

                        "probability":
                            probability,

                        "outcome":
                            outcome,

                        "next_state":
                            next_state,
                    }
                )

        if not predictions:
            raise ValueError(
                "No historical predictions generated."
            )

        brier = sum(
            (
                row["probability"]
                - row["outcome"]
            ) ** 2
            for row in predictions
        ) / len(predictions)

        observed_rate = (
            sum(
                row["outcome"]
                for row in predictions
            )
            / len(predictions)
        )

        mean_probability = (
            sum(
                row["probability"]
                for row in predictions
            )
            / len(predictions)
        )

        bins = []

        for low in [
            0.0,
            0.1,
            0.2,
            0.3,
            0.4,
            0.5,
            0.6,
            0.7,
            0.8,
            0.9,
        ]:

            high = low + 0.1

            bucket = [
                row
                for row in predictions
                if (
                    row["probability"] >= low
                    and (
                        row["probability"] < high
                        or high >= 1.0
                    )
                )
            ]

            if not bucket:
                continue

            bins.append(
                {
                    "lower":
                        round(low, 1),

                    "upper":
                        round(
                            min(
                                high,
                                1.0,
                            ),
                            1,
                        ),

                    "count":
                        len(bucket),

                    "mean_forecast":
                        round(
                            sum(
                                row[
                                    "probability"
                                ]
                                for row
                                in bucket
                            )
                            / len(bucket),
                            6,
                        ),

                    "observed_frequency":
                        round(
                            sum(
                                row[
                                    "outcome"
                                ]
                                for row
                                in bucket
                            )
                            / len(bucket),
                            6,
                        ),
                }
            )

        return {
            "model":
                "annual-armed-onset-backtest-v1",

            "validation_method":
                "leave-one-conflict-out",

            "target":
                "S0_to_S3_or_S4_next_year",

            "prediction_count":
                len(predictions),

            "observed_event_rate":
                round(
                    observed_rate,
                    6,
                ),

            "mean_forecast_probability":
                round(
                    mean_probability,
                    6,
                ),

            "brier_score":
                round(
                    brier,
                    6,
                ),

            "calibration_bins":
                bins,
        }
