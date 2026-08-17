from __future__ import annotations

import json
from pathlib import Path

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)

PATH = Path(
    "app/data/conflict_intelligence/"
    "border_dyads_seed.json"
)


def main() -> None:
    payload = json.loads(PATH.read_text())
    records = payload["records"]

    print("Records loaded:", len(records))

    if len(records) != payload["record_count"]:
        raise SystemExit("record_count mismatch")

    db = get_supabase_client()

    batch_size = 100

    for start in range(0, len(records), batch_size):
        batch = records[start:start + batch_size]

        (
            db.table("conflict_border_dyads")
            .upsert(
                batch,
                on_conflict="dyad_id",
            )
            .execute()
        )

        print(
            f"Inserted/upserted "
            f"{start + 1}-{start + len(batch)}"
        )

    print("SUCCESS")


if __name__ == "__main__":
    main()
