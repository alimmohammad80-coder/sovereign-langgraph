from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

OUTPUT = Path(
    "app/data/conflict_intelligence/"
    "governing_authorities_seed.json"
)


def main() -> None:
    today = datetime.now(timezone.utc).date().isoformat()

    records = [
        {
            "relationship_id": "GOV-AFG-TALIBAN",
            "organization_id": "NSO-TALIBAN",
            "state_iso3": "AFG",
            "territory_id": None,
            "control_scope": "national",
            "effective_control": True,
            "control_start_date": "2021-08-15",
            "control_end_date": None,
            "recognition_status":
                "not_un_recognized_government",
            "recognition_source":
                "United Nations",
            "recognition_source_url":
                "https://www.un.org/",
            "source":
                "United Nations Assistance Mission in Afghanistan",
            "source_url":
                "https://unama.unmissions.org/",
            "source_version":
                "accessed-2026-08",
            "confidence_grade":
                "high",
            "review_status":
                "validated",
            "last_reviewed":
                today,
            "active":
                True,
        }
    ]

    payload = {
        "registry_name":
            "Conflict Intelligence Governing Authorities",
        "registry_version":
            "conflict-governing-authorities-v1",
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


if __name__ == "__main__":
    main()
