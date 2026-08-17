from __future__ import annotations

import json
from pathlib import Path

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)

PATH = Path(
    "app/data/conflict_intelligence/"
    "country_aliases_seed.json"
)

payload = json.loads(PATH.read_text())
records = payload["records"]

db = get_supabase_client()

(
    db.table("conflict_country_aliases")
    .upsert(
        records,
        on_conflict="alias",
    )
    .execute()
)

print("=" * 70)
print("COUNTRY ALIASES SEEDED")
print("=" * 70)
print("Records:", len(records))
