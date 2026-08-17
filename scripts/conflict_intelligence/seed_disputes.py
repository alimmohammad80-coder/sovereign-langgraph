from __future__ import annotations

import json
from pathlib import Path

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)

PATH = Path(
    "app/data/conflict_intelligence/"
    "disputes_seed.json"
)


def main() -> None:
    payload = json.loads(
        PATH.read_text()
    )

    records = payload["records"]

    if len(records) != payload["record_count"]:
        raise SystemExit(
            "record_count mismatch"
        )

    print(
        f"Records loaded: {len(records)}"
    )

    if not records:
        print(
            "No records to insert."
        )
        return

    db = get_supabase_client()

    for start in range(
        0,
        len(records),
        100,
    ):
        batch = records[
            start:start + 100
        ]

        (
            db.table(
                "conflict_disputes"
            )
            .upsert(
                batch,
                on_conflict="dispute_id",
            )
            .execute()
        )

        print(
            f"Upserted "
            f"{start + 1}-"
            f"{start + len(batch)}"
        )

    print("SUCCESS")


if __name__ == "__main__":
    main()
