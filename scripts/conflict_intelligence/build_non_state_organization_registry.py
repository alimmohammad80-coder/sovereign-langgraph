from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

OUTPUT = Path(
    "app/data/conflict_intelligence/"
    "non_state_organizations_seed.json"
)


def main() -> None:
    today = datetime.now(timezone.utc).date().isoformat()

    records = [
        {
            "organization_id": "NSO-TALIBAN",
            "name": "Taliban",
            "aliases": [],
            "active": True,
            "areas_of_operation_iso3": ["AFG"],
            "territory_refs": [],
            "estimated_strength": None,
            "headquarters_location": None,
            "external_ids": {},
            "source": "United Nations Assistance Mission in Afghanistan",
            "source_url": "https://unama.unmissions.org/",
            "source_version": "accessed-2026-08",
            "confidence_grade": "high",
            "review_status": "validated",
            "last_reviewed": today,
        }
    ]

    ids = [r["organization_id"] for r in records]

    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate organization_id detected")

    payload = {
        "registry_name":
            "Conflict Intelligence Non-State Organizations",
        "registry_version":
            "conflict-non-state-organizations-v1",
        "generated_at":
            datetime.now(timezone.utc).isoformat(),
        "record_count": len(records),
        "records": records,
    }

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT.write_text(
        json.dumps(
            payload,
            indent=2,
        )
    )

    print(f"Created {OUTPUT}")
    print(f"Records: {len(records)}")


if __name__ == "__main__":
    main()
