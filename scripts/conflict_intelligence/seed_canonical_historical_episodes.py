from __future__ import annotations

import json
from pathlib import Path

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)

PATH = Path(
    "app/data/conflict_intelligence/"
    "canonical_historical_episodes.json"
)

payload = json.loads(PATH.read_text())
records = payload["records"]

for row in records:
    if isinstance(row.get("location"), str):
        row["location"] = [row["location"]]

db = get_supabase_client()

batch_size = 100
inserted = 0

for start in range(0, len(records), batch_size):

    batch = records[start:start + batch_size]

    (
        db.table("conflict_canonical_episodes")
        .upsert(
            batch,
            on_conflict="conflict_id",
        )
        .execute()
    )

    inserted += len(batch)

    print(
        f"Inserted/upserted "
        f"{inserted}/{len(records)}"
    )

print("=" * 70)
print("CANONICAL EPISODES SEEDED")
print("=" * 70)
print("Rows:", inserted)
