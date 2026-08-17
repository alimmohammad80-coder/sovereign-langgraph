from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

OUTPUT = Path(
    "app/data/conflict_intelligence/disputes_seed.json"
)

ALLOWED_TYPES = {
    "land_boundary",
    "territorial_sovereignty",
    "maritime_boundary",
    "eez",
    "island_sovereignty",
    "occupation",
    "separatist",
    "autonomy",
    "resource",
    "water",
    "demarcation",
    "ceasefire_line",
    "other",
}

ALLOWED_STATUSES = {
    "latent",
    "active",
    "militarized",
    "negotiating",
    "ceasefire",
    "frozen",
    "resolved",
    "unknown",
}


def validate_record(record: dict) -> None:
    required = {
        "dispute_id",
        "name",
        "dispute_type",
        "status",
        "parties",
        "claimant_iso3",
        "source",
        "review_status",
    }

    missing = required - record.keys()

    if missing:
        raise ValueError(
            f"{record.get('dispute_id')}: "
            f"missing fields {sorted(missing)}"
        )

    if record["dispute_type"] not in ALLOWED_TYPES:
        raise ValueError(
            f"Invalid dispute_type: "
            f"{record['dispute_type']}"
        )

    if record["status"] not in ALLOWED_STATUSES:
        raise ValueError(
            f"Invalid status: {record['status']}"
        )

    if not isinstance(record["parties"], list):
        raise ValueError("parties must be a list")

    if not isinstance(record["claimant_iso3"], list):
        raise ValueError("claimant_iso3 must be a list")

    if record["review_status"] == "validated":
        if not record.get("source"):
            raise ValueError(
                "Validated dispute requires source"
            )


def main() -> None:
    records: list[dict] = [
        {
            "dispute_id": "DISPUTE-IND-PAK-KASHMIR",
            "name": "Jammu and Kashmir / Line of Control",
            "dispute_type": "ceasefire_line",
            "status": "ceasefire",
            "parties": ["India", "Pakistan"],
            "primary_dyad_id": "DYAD-IND-PAK-LAND",
            "territory_id": None,
            "claimant_iso3": ["IND", "PAK"],
            "maritime": False,
            "transboundary": True,
            "start_year": 1947,
            "last_major_incident": None,
            "current_mechanism": "UNMOGIP",
            "legal_process": None,
            "geometry_ref": None,
            "source": "United Nations Peacekeeping — UNMOGIP",
            "source_url": "https://peacekeeping.un.org/en/factsheet/unmogip",
            "source_version": "accessed-2026-08",
            "confidence_grade": "high",
            "review_status": "validated",
            "last_reviewed": datetime.now(timezone.utc).date().isoformat(),
            "active": True,
        },
        {
            "dispute_id": "DISPUTE-CYP-CYPRUS",
            "name": "Cyprus Conflict and Buffer Zone",
            "dispute_type": "ceasefire_line",
            "status": "frozen",
            "parties": [
                "Republic of Cyprus",
                "Turkish Cypriot side",
                "Türkiye",
            ],
            "primary_dyad_id": None,
            "territory_id": None,
            "claimant_iso3": ["CYP", "TUR"],
            "maritime": False,
            "transboundary": False,
            "start_year": 1974,
            "last_major_incident": None,
            "current_mechanism": "UNFICYP",
            "legal_process": None,
            "geometry_ref": "United Nations Buffer Zone in Cyprus",
            "source": "United Nations Peace Operations — UNFICYP",
            "source_url": "https://unficyp.unmissions.org/en/about-unficyp",
            "source_version": "accessed-2026-08",
            "confidence_grade": "high",
            "review_status": "validated",
            "last_reviewed": datetime.now(timezone.utc).date().isoformat(),
            "active": True,
        },
        {
            "dispute_id": "DISPUTE-WESTERN-SAHARA",
            "name": "Western Sahara",
            "dispute_type": "territorial_sovereignty",
            "status": "active",
            "parties": ["Morocco", "Frente POLISARIO"],
            "primary_dyad_id": None,
            "territory_id": None,
            "claimant_iso3": ["MAR"],
            "maritime": False,
            "transboundary": False,
            "start_year": 1975,
            "last_major_incident": None,
            "current_mechanism": "MINURSO",
            "legal_process": "UN-led political process",
            "geometry_ref": "Western Sahara",
            "source": "United Nations Peace Operations — MINURSO",
            "source_url": "https://minurso.unmissions.org/en/mandate",
            "source_version": "accessed-2026-08",
            "confidence_grade": "high",
            "review_status": "validated",
            "last_reviewed": datetime.now(timezone.utc).date().isoformat(),
            "active": True,
        },
        {
            "dispute_id": "DISPUTE-GUY-VEN-ESSEQUIBO",
            "name": "Guyana–Venezuela / Essequibo",
            "dispute_type": "territorial_sovereignty",
            "status": "active",
            "parties": ["Guyana", "Venezuela"],
            "primary_dyad_id": "DYAD-GUY-VEN-LAND",
            "territory_id": None,
            "claimant_iso3": ["GUY", "VEN"],
            "maritime": False,
            "transboundary": True,
            "start_year": None,
            "last_major_incident": None,
            "current_mechanism": "International Court of Justice proceedings",
            "legal_process": "Arbitral Award of 3 October 1899 (Guyana v. Venezuela)",
            "geometry_ref": "Essequibo region",
            "source": "International Court of Justice",
            "source_url": "https://www.icj-cij.org/case/171",
            "source_version": "accessed-2026-08",
            "confidence_grade": "high",
            "review_status": "validated",
            "last_reviewed": datetime.now(timezone.utc).date().isoformat(),
            "active": True,
        },
    ]

    for record in records:
        validate_record(record)

    ids = [
        record["dispute_id"]
        for record in records
    ]

    if len(ids) != len(set(ids)):
        raise ValueError(
            "Duplicate dispute_id detected"
        )

    payload = {
        "registry_name":
            "Conflict Intelligence Global Disputes",

        "registry_version":
            "conflict-disputes-v1",

        "generated_at":
            datetime.now(timezone.utc).isoformat(),

        "source_manifest": [],

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

    print(
        f"Created {OUTPUT}"
    )

    print(
        f"Records: {len(records)}"
    )

    print(
        "No disputes populated yet."
    )


if __name__ == "__main__":
    main()
