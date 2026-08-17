from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

OUTPUT = Path(
    "app/data/conflict_intelligence/"
    "country_aliases_seed.json"
)

today = datetime.now(timezone.utc).date().isoformat()

records = [
    {
        "alias": "United States of America",
        "iso3": "USA",
        "alias_type": "official",
        "source": "Natural Earth",
        "review_status": "validated",
        "last_reviewed": today,
    },
    {
        "alias": "United States",
        "iso3": "USA",
        "alias_type": "common",
        "source": "Natural Earth",
        "review_status": "validated",
        "last_reviewed": today,
    },
    {
        "alias": "Russia",
        "iso3": "RUS",
        "alias_type": "common",
        "source": "Natural Earth",
        "review_status": "validated",
        "last_reviewed": today,
    },
    {
        "alias": "Soviet Union",
        "iso3": "RUS",
        "alias_type": "historical",
        "source": "Historical",
        "review_status": "validated",
        "last_reviewed": today,
    },
    {
        "alias": "North Macedonia",
        "iso3": "MKD",
        "alias_type": "official",
        "source": "Natural Earth",
        "review_status": "validated",
        "last_reviewed": today,
    },
    {
        "alias": "Macedonia",
        "iso3": "MKD",
        "alias_type": "historical",
        "source": "Historical",
        "review_status": "validated",
        "last_reviewed": today,
    },
    {
        "alias": "DR Congo",
        "iso3": "COD",
        "alias_type": "common",
        "source": "Natural Earth",
        "review_status": "validated",
        "last_reviewed": today,
    },
    {
        "alias": "Zaire",
        "iso3": "COD",
        "alias_type": "historical",
        "source": "Historical",
        "review_status": "validated",
        "last_reviewed": today,
    },
    {
        "alias": "Congo",
        "iso3": "COG",
        "alias_type": "common",
        "source": "Natural Earth",
        "review_status": "validated",
        "last_reviewed": today,
    },
    {
        "alias": "Rhodesia",
        "iso3": "ZWE",
        "alias_type": "historical",
        "source": "Historical",
        "review_status": "validated",
        "last_reviewed": today,
    },
    {
        "alias": "North Yemen",
        "iso3": "YEM",
        "alias_type": "historical",
        "source": "Historical",
        "review_status": "validated",
        "last_reviewed": today,
    },
    {
        "alias": "South Yemen",
        "iso3": "YEM",
        "alias_type": "historical",
        "source": "Historical",
        "review_status": "validated",
        "last_reviewed": today,
    },
    {
        "alias": "North Vietnam",
        "iso3": "VNM",
        "alias_type": "historical",
        "source": "Historical",
        "review_status": "validated",
        "last_reviewed": today,
    },
    {
        "alias": "South Vietnam",
        "iso3": "VNM",
        "alias_type": "historical",
        "source": "Historical",
        "review_status": "validated",
        "last_reviewed": today,
    },
    {
        "alias": "Kampuchea",
        "iso3": "KHM",
        "alias_type": "historical",
        "source": "Historical",
        "review_status": "validated",
        "last_reviewed": today,
    },
]

payload = {
    "registry_name": "Conflict Country Alias Registry",
    "registry_version": "country-aliases-v1",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "record_count": len(records),
    "records": records,
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(payload, indent=2))

print("=" * 70)
print("COUNTRY ALIAS REGISTRY")
print("=" * 70)
print("Records:", len(records))
print("Output:", OUTPUT)
