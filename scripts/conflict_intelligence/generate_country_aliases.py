from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)

OUTPUT = Path(
    "app/data/conflict_intelligence/"
    "country_aliases_seed.json"
)

today = datetime.now(timezone.utc).date().isoformat()

db = get_supabase_client()

countries = (
    db.table("conflict_countries")
    .select("iso3,name,official_name")
    .execute()
    .data
    or []
)

records = []
seen = set()


def add(alias: str | None,
        iso3: str,
        alias_type: str):

    if not alias:
        return

    alias = alias.strip()

    if not alias:
        return

    key = (alias.lower(), iso3)

    if key in seen:
        return

    seen.add(key)

    records.append(
        {
            "alias": alias,
            "iso3": iso3,
            "alias_type": alias_type,
            "source": "Conflict Countries Registry",
            "review_status": "validated",
            "last_reviewed": today,
            "active": True,
        }
    )


for country in countries:

    iso3 = country["iso3"]

    name = country.get("name")
    official = country.get("official_name")

    add(name, iso3, "primary")
    add(official, iso3, "official")

    if name:

        n = name

        add(
            n.replace("Republic of ", ""),
            iso3,
            "common",
        )

        add(
            n.replace("Kingdom of ", ""),
            iso3,
            "common",
        )

        add(
            n.replace("State of ", ""),
            iso3,
            "common",
        )

        add(
            n.replace(
                "Democratic Republic of ",
                "",
            ),
            iso3,
            "common",
        )

        add(
            n.replace(
                "People's Republic of ",
                "",
            ),
            iso3,
            "common",
        )

        add(
            n.replace(
                "Islamic Republic of ",
                "",
            ),
            iso3,
            "common",
        )

        add(
            n.replace(
                "Federated States of ",
                "",
            ),
            iso3,
            "common",
        )

payload = {
    "registry_name": "Conflict Country Alias Registry",
    "registry_version": "country-aliases-v2",
    "generated_at": datetime.now(
        timezone.utc
    ).isoformat(),
    "record_count": len(records),
    "records": records,
}

OUTPUT.write_text(
    json.dumps(
        payload,
        indent=2,
    )
)

print("=" * 70)
print("COUNTRY ALIAS REGISTRY GENERATED")
print("=" * 70)
print("Countries:", len(countries))
print("Aliases:", len(records))
print("Output:", OUTPUT)
