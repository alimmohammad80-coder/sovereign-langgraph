from __future__ import annotations

import pandas as pd

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)

SOURCE = (
    "data/processed/"
    "conflict_state_timeline.csv"
)

df = pd.read_csv(
    SOURCE,
    dtype=str,
)

for column in [
    "conflict_id",
    "year",
    "intensity",
]:
    df[column] = pd.to_numeric(
        df[column],
        errors="coerce",
    ).astype("Int64")

records = []

for row in df.to_dict("records"):

    clean = {}

    for key, value in row.items():

        if pd.isna(value):
            clean[key] = None

        elif hasattr(value, "item"):
            clean[key] = value.item()

        else:
            clean[key] = value

    clean["active"] = (
        str(clean.get("active"))
        .lower()
        == "true"
    )

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
            "conflict_state_timeline"
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
print("STATE TIMELINE SEEDED")
print("=" * 70)
print("Rows:", inserted)
