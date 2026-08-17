from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

OUTPUT = Path(
    "app/data/conflict_intelligence/"
    "frozen_conflicts_seed.json"
)


def validate_record(record: dict) -> None:
    required = {
        "fc_id",
        "name",
        "parties",
        "current_status",
        "source",
        "review_status",
    }

    missing = required - record.keys()

    if missing:
        raise ValueError(
            f"{record.get('fc_id')}: "
            f"missing fields {sorted(missing)}"
        )

    if not isinstance(record["parties"], list):
        raise ValueError(
            "parties must be a list"
        )

    score = record.get(
        "reactivation_hazard_score"
    )

    if score is not None:
        if not 0 <= score <= 100:
            raise ValueError(
                "reactivation_hazard_score "
                "must be 0–100"
            )


def main() -> None:
    today = datetime.now(timezone.utc).date().isoformat()

    records: list[dict] = [
        {
            "fc_id": "FC-CYP-CYPRUS",
            "name": "Cyprus Ceasefire and Buffer Zone",
            "dispute_id": "DISPUTE-CYP-CYPRUS",
            "parties": [
                "Republic of Cyprus",
                "Turkish Cypriot side",
                "Türkiye",
            ],
            "territory_id": "TERRITORY-CYPRUS-BUFFER-ZONE",
            "primary_dyad_id": None,
            "freeze_year": 1974,
            "last_flare_date": None,
            "mediation_regime": (
                "United Nations-led Cyprus settlement process / UNFICYP"
            ),
            "peacekeeping_presence": True,
            "current_status": "frozen_unresolved",
            "reactivation_hazard_score": None,
            "hazard_confidence": "unknown",
            "window_watch": False,
            "active": True,
            "source": "United Nations Peace Operations — UNFICYP",
            "source_version": "accessed-2026-08",
            "review_status": "validated",
            "last_reviewed": today,
        },
        {
            "fc_id": "FC-IND-PAK-KASHMIR",
            "name": "Jammu and Kashmir / Line of Control",
            "dispute_id": "DISPUTE-IND-PAK-KASHMIR",
            "parties": [
                "India",
                "Pakistan",
            ],
            "territory_id": "TERRITORY-KASHMIR",
            "primary_dyad_id": "DYAD-IND-PAK-LAND",
            "freeze_year": 1949,
            "last_flare_date": None,
            "mediation_regime": (
                "United Nations Military Observer Group "
                "in India and Pakistan (UNMOGIP)"
            ),
            "peacekeeping_presence": True,
            "current_status": "ceasefire_unresolved",
            "reactivation_hazard_score": None,
            "hazard_confidence": "unknown",
            "window_watch": False,
            "active": True,
            "source": "United Nations — UNMOGIP",
            "source_version": "accessed-2026-08",
            "review_status": "validated",
            "last_reviewed": today,
        },
        {
            "fc_id": "FC-WESTERN-SAHARA",
            "name": "Western Sahara Conflict",
            "dispute_id": "DISPUTE-WESTERN-SAHARA",
            "parties": [
                "Morocco",
                "Frente POLISARIO",
            ],
            "territory_id": "TERRITORY-WESTERN-SAHARA",
            "primary_dyad_id": None,
            "freeze_year": 1991,
            "last_flare_date": None,
            "mediation_regime": (
                "United Nations-led political process / MINURSO"
            ),
            "peacekeeping_presence": True,
            "current_status": "unresolved_monitored",
            "reactivation_hazard_score": None,
            "hazard_confidence": "unknown",
            "window_watch": False,
            "active": True,
            "source": "United Nations Peace Operations — MINURSO",
            "source_version": "accessed-2026-08",
            "review_status": "validated",
            "last_reviewed": today,
        },
    ]

    for record in records:
        validate_record(record)

    ids = [
        record["fc_id"]
        for record in records
    ]

    if len(ids) != len(set(ids)):
        raise ValueError(
            "Duplicate fc_id detected"
        )

    payload = {
        "registry_name":
            "Conflict Intelligence Frozen Conflicts",

        "registry_version":
            "conflict-frozen-conflicts-v1",

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

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
    print(
        "No frozen conflicts populated yet."
    )


if __name__ == "__main__":
    main()
