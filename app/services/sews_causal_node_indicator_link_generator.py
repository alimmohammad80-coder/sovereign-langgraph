from __future__ import annotations

from collections import defaultdict
from typing import Any

from supabase import Client


GENERATOR_VERSION = "sews-causal-node-link-generator-v1"

CLASS_TO_NODE_ROLE = {
    "PRECURSOR": "PRECURSOR_ACTIVITY",
    "ACCELERANT": "ACCELERATION",
    "TRIGGER": "TRIGGER_EVENT",
    "CONTRA": "MITIGATION",
    "OUTCOME": "OUTCOME",
}

CLASS_TO_INFLUENCE = {
    "PRECURSOR": "SUPPORTING",
    "ACCELERANT": "SUPPORTING",
    "TRIGGER": "SUPPORTING",
    "CONTRA": "CONTRADICTING",
    "OUTCOME": "SUPPORTING",
}


class SEWSCausalNodeIndicatorLinkGeneratorError(RuntimeError):
    pass


class SEWSCausalNodeIndicatorLinkGenerator:
    def __init__(self, db: Client):
        self.db = db

    @staticmethod
    def _node_role(node_key: str | None) -> str | None:
        value = str(node_key or "").upper().strip()
        marker = "-NODE-"
        if marker not in value:
            return None
        return value.rsplit(marker, 1)[-1]

    @staticmethod
    def _normalized_weight(value: Any) -> float:
        try:
            weight = float(value or 1.0)
        except (TypeError, ValueError):
            weight = 1.0
        return round(min(10.0, max(0.1, weight)), 6)

    def _active_problem_keys(self) -> list[str]:
        rows = (
            self.db.table("sews_warning_problems")
            .select("problem_key")
            .eq("active", True)
            .range(0, 4999)
            .execute()
            .data
            or []
        )
        return sorted({
            str(row["problem_key"])
            for row in rows
            if row.get("problem_key")
        })

    def _nodes(self, problem_keys: list[str]) -> list[dict[str, Any]]:
        if not problem_keys:
            return []
        return (
            self.db.table("sews_causal_nodes")
            .select("id,node_key,problem_key,node_type,active")
            .in_("problem_key", problem_keys)
            .eq("active", True)
            .range(0, 4999)
            .execute()
            .data
            or []
        )

    def _mappings(self, problem_keys: list[str]) -> list[dict[str, Any]]:
        if not problem_keys:
            return []
        return (
            self.db.table("sews_warning_problem_indicators")
            .select(
                "problem_key,indicator_key,indicator_class,"
                "weight,polarity,active"
            )
            .in_("problem_key", problem_keys)
            .eq("active", True)
            .range(0, 9999)
            .execute()
            .data
            or []
        )

    def _existing_links(self) -> set[tuple[str, str, str]]:
        rows = (
            self.db.table("sews_causal_node_indicator_links")
            .select("node_id,indicator_key,influence_type")
            .range(0, 99999)
            .execute()
            .data
            or []
        )
        return {
            (
                str(row["node_id"]),
                str(row["indicator_key"]),
                str(row["influence_type"]).upper(),
            )
            for row in rows
            if row.get("node_id")
            and row.get("indicator_key")
            and row.get("influence_type")
        }

    def generate_all(self) -> dict[str, Any]:
        problem_keys = self._active_problem_keys()

        if not problem_keys:
            raise SEWSCausalNodeIndicatorLinkGeneratorError(
                "No active SEWS warning problems were found."
            )

        nodes = self._nodes(problem_keys)
        mappings = self._mappings(problem_keys)
        existing = self._existing_links()

        node_lookup: dict[tuple[str, str], dict[str, Any]] = {}
        nodes_by_problem: dict[str, int] = defaultdict(int)

        for node in nodes:
            problem_key = str(node.get("problem_key") or "")
            role = self._node_role(node.get("node_key"))
            if not problem_key or not role:
                continue
            node_lookup[(problem_key, role)] = node
            nodes_by_problem[problem_key] += 1

        links_created = 0
        links_skipped = 0
        skipped_by_reason: dict[str, int] = defaultdict(int)
        linked_problem_keys: set[str] = set()

        for mapping in mappings:
            problem_key = str(mapping.get("problem_key") or "")
            indicator_key = str(mapping.get("indicator_key") or "")
            indicator_class = str(
                mapping.get("indicator_class") or ""
            ).upper()

            if not problem_key or not indicator_key:
                links_skipped += 1
                skipped_by_reason["missing_mapping_identity"] += 1
                continue

            role = CLASS_TO_NODE_ROLE.get(indicator_class)
            influence_type = CLASS_TO_INFLUENCE.get(indicator_class)

            if not role or not influence_type:
                links_skipped += 1
                skipped_by_reason["unsupported_indicator_class"] += 1
                continue

            node = node_lookup.get((problem_key, role))
            if not node:
                links_skipped += 1
                skipped_by_reason["causal_node_not_found"] += 1
                continue

            node_id = str(node["id"])
            identity = (node_id, indicator_key, influence_type)

            if identity in existing:
                links_skipped += 1
                skipped_by_reason["already_exists"] += 1
                continue

            row = {
                "node_id": node_id,
                "indicator_key": indicator_key,
                "influence_type": influence_type,
                "influence_weight": self._normalized_weight(
                    mapping.get("weight")
                ),
                "active": True,
            }

            result = (
                self.db.table("sews_causal_node_indicator_links")
                .insert(row)
                .execute()
            )

            if not result.data:
                raise SEWSCausalNodeIndicatorLinkGeneratorError(
                    "Insert returned no row for "
                    f"{problem_key}:{indicator_key}."
                )

            existing.add(identity)
            linked_problem_keys.add(problem_key)
            links_created += 1

        return {
            "generator_version": GENERATOR_VERSION,
            "warning_problems_processed": len(problem_keys),
            "warning_problems_with_nodes": len(nodes_by_problem),
            "warning_problems_linked_this_run": len(linked_problem_keys),
            "nodes_processed": len(nodes),
            "indicator_mappings_processed": len(mappings),
            "links_created": links_created,
            "links_skipped": links_skipped,
            "skipped_by_reason": dict(sorted(skipped_by_reason.items())),
            "total_links_after_run": len(existing),
        }
