from __future__ import annotations

from typing import Any

from supabase import Client


CLASS_TO_ROLE = {
    "PRECURSOR": "PRECURSOR_ACTIVITY",
    "ACCELERANT": "ACCELERATION",
    "TRIGGER": "TRIGGER_EVENT",
    "CONTRA": "MITIGATION",
}


class SEWSGlobalCausalLinkGenerator:
    def __init__(self, db: Client):
        self.db = db

    def generate_all(self) -> dict[str, Any]:
        nodes = (
            self.db.table("sews_causal_nodes")
            .select("id,node_key,problem_key")
            .eq("active", True)
            .range(0, 4999)
            .execute()
            .data
            or []
        )

        node_lookup = {
            (row["problem_key"], row["node_key"].split("-NODE-")[-1]): row["id"]
            for row in nodes
        }

        mappings = (
            self.db.table("sews_warning_problem_indicators")
            .select("problem_key,indicator_key,indicator_class,weight,active")
            .eq("active", True)
            .range(0, 9999)
            .execute()
            .data
            or []
        )

        created = 0
        skipped = 0

        for mapping in mappings:
            indicator_class = str(
                mapping.get("indicator_class") or ""
            ).upper()

            role = CLASS_TO_ROLE.get(indicator_class)
            node_id = node_lookup.get(
                (mapping["problem_key"], role)
            )

            if not role or not node_id:
                skipped += 1
                continue

            influence_type = (
                "CONTRADICTING"
                if indicator_class == "CONTRA"
                else "SUPPORTING"
            )

            row = {
                "node_id": node_id,
                "indicator_key": mapping["indicator_key"],
                "influence_type": influence_type,
                "influence_weight": min(
                    10.0,
                    max(0.1, float(mapping.get("weight") or 1.0)),
                ),
                "active": True,
            }

            (
                self.db.table("sews_causal_node_indicator_links")
                .upsert(
                    row,
                    on_conflict="node_id,indicator_key,influence_type",
                )
                .execute()
            )

            created += 1

        return {
            "links_created": created,
            "links_skipped": skipped,
        }
