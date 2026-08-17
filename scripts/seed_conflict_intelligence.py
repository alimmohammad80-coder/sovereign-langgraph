from __future__ import annotations

import json
from pathlib import Path

from app.repositories.conflict_intelligence_repository import get_supabase_client


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "app" / "data" / "conflict_intelligence"


def load_seed(filename: str) -> list[dict]:
    payload = json.loads((DATA_DIR / filename).read_text())
    records = payload.get("records", [])
    if payload.get("record_count") != len(records):
        raise ValueError(f"{filename}: record_count does not match records length")
    return records


def upsert(table: str, records: list[dict], conflict_key: str) -> None:
    if not records:
        print(f"{table}: no records to seed")
        return
    client = get_supabase_client()
    client.table(table).upsert(records, on_conflict=conflict_key).execute()
    print(f"{table}: seeded {len(records)} records")


def main() -> None:
    upsert("conflict_countries", load_seed("countries_seed.json"), "iso3")
    upsert(
        "conflict_frozen_conflicts",
        load_seed("frozen_conflicts_seed.json"),
        "fc_id",
    )


if __name__ == "__main__":
    main()
