from __future__ import annotations

import pandas as pd

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)


class HistoricalEpisodeBuilder:

    def __init__(self, source_file: str):

        self.db = get_supabase_client()

        self.df = pd.read_csv(
            source_file,
            low_memory=False,
            dtype=str,
        )

        aliases = (
            self.db.table("conflict_country_aliases")
            .select("alias,iso3")
            .execute()
            .data
            or []
        )

        self.alias_lookup = {
            r["alias"].lower(): r["iso3"]
            for r in aliases
        }

    def resolve(self, value):

        if not value:
            return None

        value = (
            str(value)
            .replace("Government of ", "")
            .replace("(Burma)", "")
            .replace("(Soviet Union)", "")
            .replace("(North Vietnam)", "")
            .strip()
        )

        return self.alias_lookup.get(
            value.lower()
        )

    def build(self):

        episodes = []

        for _, row in self.df.iterrows():

            episodes.append(
                {
                    "conflict_id": row["conflict_id"],
                    "year": int(row["year"]),
                    "location": row["location"],
                    "region": row["region"],
                    "side_a": self.resolve(row["side_a"]),
                    "side_b": self.resolve(row["side_b"]),
                    "intensity": row["intensity_level"],
                    "type": row["type_of_conflict"],
                    "territory": row["territory_name"],
                    "start_date": row["start_date"],
                    "episode_end": row["ep_end"],
                }
            )

        self.episodes = pd.DataFrame(episodes)

        print("=" * 70)
        print("HISTORICAL EPISODES")
        print("=" * 70)
        print("Episodes:", len(self.episodes))
        print()
        print(self.episodes.head(20))

        self.episodes.to_csv(
            "data/processed/historical_episodes.csv",
            index=False,
        )

        print()
        print("Saved:")
        print("data/processed/historical_episodes.csv")
