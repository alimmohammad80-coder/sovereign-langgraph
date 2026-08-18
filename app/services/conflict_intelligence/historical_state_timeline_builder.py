from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)

SOURCE = Path(
    "data/processed/historical_episodes.csv"
)

OUTPUT = Path(
    "data/processed/conflict_state_timeline.csv"
)


class HistoricalStateTimelineBuilder:

    def __init__(self) -> None:
        self.df = pd.read_csv(
            SOURCE,
            dtype=str,
        )

        self.db = get_supabase_client()

        canonical = (
            self.db.table(
                "conflict_canonical_episodes"
            )
            .select(
                "id,conflict_id"
            )
            .execute()
            .data
            or []
        )

        self.canonical_lookup = {
            int(row["conflict_id"]):
                str(row["id"])
            for row in canonical
        }

    @staticmethod
    def classify_observed_state(
        intensity: int | None,
        side_a: str | None,
        side_b: str | None,
    ) -> tuple[str, str]:

        # UCDP/PRIO intensity level:
        #
        # 1 = minor armed conflict
        # 2 = war
        #
        # Do not infer pre-conflict tension/crisis states
        # from UCDP battle-death intensity alone.

        if intensity == 2:
            return (
                "S4_WAR",
                "ucdp_intensity_2_war",
            )

        if intensity == 1:
            return (
                "S3_LIMITED_CONFLICT",
                "ucdp_intensity_1_armed_conflict",
            )

        return (
            "S0_STABLE",
            "no_recorded_armed_conflict",
        )

    def build(self) -> pd.DataFrame:

        df = self.df.copy()

        df["conflict_id"] = pd.to_numeric(
            df["conflict_id"],
            errors="coerce",
        ).astype("Int64")

        df["year"] = pd.to_numeric(
            df["year"],
            errors="coerce",
        ).astype("Int64")

        df["intensity"] = pd.to_numeric(
            df["intensity"],
            errors="coerce",
        ).astype("Int64")

        df = df.dropna(
            subset=[
                "conflict_id",
                "year",
            ]
        )

        records = []

        for conflict_id, group in df.groupby(
            "conflict_id"
        ):

            conflict_id = int(
                conflict_id
            )

            group = group.sort_values(
                "year"
            )

            start_year = int(
                group["year"].min()
            )

            end_year = int(
                group["year"].max()
            )

            canonical_episode_id = (
                self.canonical_lookup.get(
                    conflict_id
                )
            )

            by_year = {}

            for _, row in group.iterrows():

                year = int(
                    row["year"]
                )

                intensity = (
                    int(row["intensity"])
                    if pd.notna(
                        row["intensity"]
                    )
                    else None
                )

                side_a = (
                    str(row["side_a"]).strip()
                    if pd.notna(
                        row["side_a"]
                    )
                    else None
                )

                side_b = (
                    str(row["side_b"]).strip()
                    if pd.notna(
                        row["side_b"]
                    )
                    else None
                )

                by_year[year] = {
                    "intensity":
                        intensity,
                    "side_a":
                        side_a,
                    "side_b":
                        side_b,
                }

            for year in range(
                start_year,
                end_year + 1,
            ):

                observed = by_year.get(
                    year
                )

                if observed:

                    state_code, reason = (
                        self.classify_observed_state(
                            observed[
                                "intensity"
                            ],
                            observed[
                                "side_a"
                            ],
                            observed[
                                "side_b"
                            ],
                        )
                    )

                    intensity = observed[
                        "intensity"
                    ]

                else:

                    state_code = (
                        "S0_STABLE"
                    )

                    reason = (
                        "no_ucdp_armed_conflict_record"
                    )

                    intensity = None

                records.append(
                    {
                        "conflict_id":
                            conflict_id,

                        "canonical_episode_id":
                            canonical_episode_id,

                        "year":
                            year,

                        "state_code":
                            state_code,

                        "intensity":
                            intensity,

                        "transition_reason":
                            reason,

                        "source":
                            "UCDP/PRIO",

                        "source_version":
                            "26.1",

                        "active":
                            True,

                        "review_status":
                            "validated",
                    }
                )

        result = pd.DataFrame(
            records
        )

        result = result.sort_values(
            [
                "conflict_id",
                "year",
            ]
        )

        OUTPUT.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        result.to_csv(
            OUTPUT,
            index=False,
        )

        print("=" * 70)
        print(
            "CONTINUOUS HISTORICAL STATE TIMELINE"
        )
        print("=" * 70)

        print(
            "Rows:",
            len(result),
        )

        print(
            "Conflicts:",
            result[
                "conflict_id"
            ].nunique(),
        )

        print(
            "Canonical links:",
            result[
                "canonical_episode_id"
            ].notna().sum(),
        )

        print()

        print(
            result[
                "state_code"
            ]
            .value_counts()
            .to_string()
        )

        print()

        print(
            "Output:",
            OUTPUT,
        )

        return result
