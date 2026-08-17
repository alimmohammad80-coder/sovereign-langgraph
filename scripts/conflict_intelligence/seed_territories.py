from __future__ import annotations

import json
from pathlib import Path

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)

PATH = Path(
    "app/data/conflict_intelligence/"
    "territories_seed.json"
)


def main() -> None:
    payload = json.loads(PATH.read_text())
    records = payload["records"]

    if len(records) != payload["record_count"]:
        raise SystemExit("record_count mismatch")

    print(f"Records loaded: {len(records)}")

    if not records:
        print("No records to insert.")
        return

    db = get_supabase_client()

    (
        db.table("conflict_territories")
        .upsert(
            records,
            on_conflict="territory_id",
        )
        .execute()
    )

    print(f"Inserted/upserted: {len(records)}")
    print("SUCCESS")


if __name__ == "__main__":
    main()
