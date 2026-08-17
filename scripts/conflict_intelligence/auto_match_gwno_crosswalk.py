from __future__ import annotations

import json
from pathlib import Path

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)

PATH = Path(
    "app/data/conflict_intelligence/"
    "gwno_country_crosswalk.json"
)

payload = json.loads(PATH.read_text())

db = get_supabase_client()

countries = (
    db.table("conflict_countries")
    .select("iso3,name")
    .execute()
    .data
    or []
)

lookup = {
    c["name"].lower(): c["iso3"]
    for c in countries
}

matched = 0

for record in payload["records"]:

    for candidate in record["candidate_names"]:

        name = (
            candidate
            .replace("Government of ", "")
            .replace(" (Soviet Union)", "")
            .replace(" (Burma)", "")
            .replace("Republic of ", "")
            .strip()
            .lower()
        )

        if name in lookup:
            record["iso3"] = lookup[name]
            matched += 1
            break

PATH.write_text(
    json.dumps(
        payload,
        indent=2,
    )
)

print("=" * 70)
print("GWNO AUTO MATCH")
print("=" * 70)
print("Matched:", matched)
print("Remaining:", payload["record_count"] - matched)
