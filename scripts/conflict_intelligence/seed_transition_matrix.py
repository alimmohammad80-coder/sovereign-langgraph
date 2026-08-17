from __future__ import annotations

import json
from pathlib import Path

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)


PATH = Path(
    "app/data/conflict_intelligence/"
    "state_transition_matrix.json"
)

payload = json.loads(
    PATH.read_text()
)

records = payload["records"]

db = get_supabase_client()

(
    db.table(
        "conflict_state_transitions"
    )
    .upsert(
        records,
        on_conflict=(
            "matrix_version,"
            "from_state,"
            "to_state"
        ),
    )
    .execute()
)

print("=" * 70)
print("TRANSITION MATRIX SEEDED")
print("=" * 70)
print(
    "Rows:",
    len(records),
)
