from __future__ import annotations

import pandas as pd

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)

SOURCE = "data/processed/historical_episodes.csv"

df = pd.read_csv(
    SOURCE,
    dtype=str,
)

df = df.rename(
    columns={
        "side_a": "side_a_iso3",
        "side_b": "side_b_iso3",
        "intensity": "intensity",
        "type": "conflict_type",
        "territory": "territory",
    }
)

columns = [
    "conflict_id",
    "year",
    "location",
    "region",
    "side_a_iso3",
    "side_b_iso3",
    "intensity",
    "conflict_type",
    "territory",
    "start_date",
    "episode_end",
]

df = df[columns].copy()

for column in [
    "conflict_id",
    "year",
    "region",
    "intensity",
    "conflict_type",
]:
    df[column] = pd.to_numeric(
        df[column],
        errors="coerce",
    ).astype("Int64")

df["episode_end"] = (
    df["episode_end"]
    .fillna("0")
    .astype(str)
    .str.strip()
    .map(
        {
            "1": True,
            "0": False,
            "true": True,
            "false": False,
            "True": True,
            "False": False,
        }
    )
    .fillna(False)
)

records = []

for row in df.to_dict("records"):
    clean = {}

    for key, value in row.items():

        if pd.isna(value):
            clean[key] = None
            continue

        if hasattr(value, "item"):
            value = value.item()

        clean[key] = value

    records.append(clean)

db = get_supabase_client()

batch_size = 250
inserted = 0

for start in range(
    0,
    len(records),
    batch_size,
):
    batch = records[
        start:start + batch_size
    ]

    (
        db.table(
            "conflict_historical_episodes"
        )
        .upsert(
            batch,
            on_conflict="conflict_id,year",
        )
        .execute()
    )

    inserted += len(batch)

    print(
        f"Inserted/upserted "
        f"{inserted}/{len(records)}"
    )

print("=" * 70)
print("HISTORICAL EPISODES SEEDED")
print("=" * 70)
print("Rows:", inserted)
