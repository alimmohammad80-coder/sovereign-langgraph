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

payload = json.loads(PATH.read_text())

records = payload["records"]
matrix_version = payload["matrix_version"]

db = get_supabase_client()

# A matrix build is an atomic model artifact.
# Remove the previous rows for this exact version before loading it.
(
    db.table("conflict_state_transitions")
    .delete()
    .eq("matrix_version", matrix_version)
    .execute()
)

(
    db.table("conflict_state_transitions")
    .insert(records)
    .execute()
)

print("=" * 70)
print("TRANSITION MATRIX SEEDED")
print("=" * 70)
print("Version:", matrix_version)
print("Rows:", len(records))
