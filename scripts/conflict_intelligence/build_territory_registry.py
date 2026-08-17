from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

OUTPUT = Path(
    "app/data/conflict_intelligence/"
    "territories_seed.json"
)


def main() -> None:
    today = datetime.now(timezone.utc).date().isoformat()

    records = [
        {
            "territory_id": "TERRITORY-KASHMIR",
            "name": "Jammu and Kashmir / Kashmir Disputed Area",
            "de_jure_iso3": None,
            "de_facto_controller": "Multiple administrations",
            "status": "disputed",
            "claimants": [
                "India",
                "Pakistan",
            ],
            "geometry_ref": None,
            "active": True,
            "source": "United Nations — UNMOGIP",
            "source_version": "accessed-2026-08",
            "confidence_grade": "high",
            "review_status": "validated",
            "last_reviewed": today,
        },
        {
            "territory_id": "TERRITORY-CYPRUS-BUFFER-ZONE",
            "name": "United Nations Buffer Zone in Cyprus",
            "de_jure_iso3": None,
            "de_facto_controller": "UN-administered buffer zone",
            "status": "frozen_entity",
            "claimants": [
                "Republic of Cyprus",
                "Turkish Cypriot side",
            ],
            "geometry_ref": "UN Buffer Zone in Cyprus",
            "active": True,
            "source": "United Nations Peace Operations — UNFICYP",
            "source_version": "accessed-2026-08",
            "confidence_grade": "high",
            "review_status": "validated",
            "last_reviewed": today,
        },
        {
            "territory_id": "TERRITORY-WESTERN-SAHARA",
            "name": "Western Sahara",
            "de_jure_iso3": None,
            "de_facto_controller": "Multiple administrations",
            "status": "unresolved",
            "claimants": [
                "Morocco",
                "Frente POLISARIO",
            ],
            "geometry_ref": "Western Sahara",
            "active": True,
            "source": "United Nations — MINURSO",
            "source_version": "accessed-2026-08",
            "confidence_grade": "high",
            "review_status": "validated",
            "last_reviewed": today,
        },
        {
            "territory_id": "TERRITORY-ESSEQUIBO",
            "name": "Essequibo",
            "de_jure_iso3": None,
            "de_facto_controller": "Guyana",
            "status": "disputed",
            "claimants": [
                "Guyana",
                "Venezuela",
            ],
            "geometry_ref": "Essequibo region",
            "active": True,
            "source": "International Court of Justice",
            "source_version": "accessed-2026-08",
            "confidence_grade": "high",
            "review_status": "validated",
            "last_reviewed": today,
        },
    ]

    ids = [
        record["territory_id"]
        for record in records
    ]

    if len(ids) != len(set(ids)):
        raise ValueError(
            "Duplicate territory_id detected"
        )

    payload = {
        "registry_name":
            "Conflict Intelligence Territories",

        "registry_version":
            "conflict-territories-v1",

        "generated_at":
            datetime.now(timezone.utc).isoformat(),

        "record_count":
            len(records),

        "records":
            records,
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

    for record in records:
        print(
            record["territory_id"],
            "|",
            record["status"],
        )


if __name__ == "__main__":
    main()
