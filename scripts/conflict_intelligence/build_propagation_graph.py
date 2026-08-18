from __future__ import annotations

import json
from pathlib import Path

from app.services.conflict_intelligence.propagation_graph_builder import (
    PropagationGraphBuilder,
)


OUTPUT = Path(
    "app/data/conflict_intelligence/"
    "propagation_graph.json"
)

result = (
    PropagationGraphBuilder()
    .build()
)

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT.write_text(
    json.dumps(
        result,
        indent=2,
        ensure_ascii=False,
    )
)

print("=" * 70)
print("GLOBAL CONFLICT PROPAGATION GRAPH")
print("=" * 70)

print(
    "Version:",
    result["graph_version"],
)

print(
    "Nodes:",
    result["node_count"],
)

print(
    "Edges:",
    result["edge_count"],
)

print()
print("NODE TYPES")
print("-" * 70)

for key, value in (
    result[
        "node_types"
    ].items()
):
    print(
        f"{key}: {value}"
    )

print()
print("RELATIONSHIPS")
print("-" * 70)

for key, value in (
    result[
        "relationship_counts"
    ].items()
):
    print(
        f"{key}: {value}"
    )

print()
print(
    "Output:",
    OUTPUT,
)
