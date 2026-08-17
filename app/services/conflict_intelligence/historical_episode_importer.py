from __future__ import annotations

from pathlib import Path

import pandas as pd


class HistoricalEpisodeImporter:

    def __init__(self, source_file: str):
        self.source_file = Path(source_file)
        self.df = None

    def load(self):
        suffix = self.source_file.suffix.lower()

        if suffix == ".csv":
            self.df = pd.read_csv(
                self.source_file,
                low_memory=False,
            )
        else:
            self.df = pd.read_excel(
                self.source_file,
            )

        print(f"Loaded {len(self.df)} rows")

    def normalize(self):

        self.df.columns = [
            c.strip().lower().replace(" ", "_")
            for c in self.df.columns
        ]

        print(
            f"Normalized {len(self.df.columns)} columns"
        )

        print(self.df.columns.tolist())


    def match_states(self):

        print("=" * 70)
        print("STATE PARTICIPANT ANALYSIS")
        print("=" * 70)

        print(
            "Unique GWNO A:",
            self.df["gwno_a"].dropna().nunique()
        )

        print(
            "Unique GWNO B:",
            self.df["gwno_b"].dropna().nunique()
        )

        print(
            "Unique Conflict Locations:",
            self.df["gwno_loc"].dropna().nunique()
        )

        print()

        print("Sample Side A values:")

        for value in (
            self.df["side_a"]
            .dropna()
            .unique()[:20]
        ):
            print(" -", value)

        print()

        print("Sample Side B values:")

        for value in (
            self.df["side_b"]
            .dropna()
            .unique()[:20]
        ):
            print(" -", value)


    def match_dyads(self):
        print("Dyad matching pending.")

    def match_disputes(self):
        print("Dispute matching pending.")

    def match_frozen_conflicts(self):
        print("Frozen conflict matching pending.")

    def validate(self):
        print(
            f"Dataset rows: {len(self.df)}"
        )

    def export_seed(self):
        print(
            "Historical episode export pending."
        )
