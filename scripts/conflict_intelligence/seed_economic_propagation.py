from __future__ import annotations

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)

from app.services.conflict_intelligence.economic_propagation_builder import (
    EconomicPropagationBuilder,
)


builder = EconomicPropagationBuilder()

payload = builder.build()

records = payload["records"]

db = get_supabase_client()

# Treat this generated economic layer as authoritative.
(
    db.table(
        "conflict_propagation_edges"
    )
    .delete()
    .eq(
        "method",
        builder.METHOD,
    )
    .execute()
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

    inserted += len(batch)

    print(
        f"Inserted/upserted "
        f"{inserted}/{len(records)}"
    )

print("=" * 70)
print("ECONOMIC PROPAGATION SEEDED")
print("=" * 70)
print(
    "Countries:",
    payload["country_count"],
)
print(
    "Skipped:",
    payload["skipped_country_count"],
)
print(
    "Edges:",
    inserted,
)
