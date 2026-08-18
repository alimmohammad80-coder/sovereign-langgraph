from __future__ import annotations

import json
from pathlib import Path

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)


PATH = Path(
    "app/data/conflict_intelligence/"
    "propagation_graph.json"
)

payload = json.loads(
    PATH.read_text()
)

records = payload[
    "records"
]

db = get_supabase_client()

# The generated propagation graph is authoritative.
# Remove ontology-derived edges from the previous build
# before loading the current graph so renamed/canonicalized
# nodes cannot survive as stale relationships.
(
    db.table(
        "conflict_propagation_edges"
    )
    .delete()
    .eq(
        "method",
        "ontology-derived",
    )
    .execute()
)

print(
    "Cleared previous ontology-derived "
    "propagation edges."
)

batch_size = 250
inserted = 0

for start in range(
    0,
    len(records),
    batch_size,
):

    batch = records[
        start:
        start + batch_size
    ]

    (
        db.table(
            "conflict_propagation_edges"
        )
        .upsert(
            batch,
            on_conflict="edge_key",
        )
        .execute()
    )

    inserted += len(
        batch
    )

    print(
        f"Inserted/upserted "
        f"{inserted}/{len(records)}"
    )

print("=" * 70)
print("PROPAGATION GRAPH SEEDED")
print("=" * 70)

print(
    "Version:",
    payload[
        "graph_version"
    ],
)

print(
    "Rows:",
    inserted,
)
