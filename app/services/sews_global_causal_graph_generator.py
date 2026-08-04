from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from supabase import Client


REGISTRY_PATH = Path(
    "app/data/sews_global_warning_registry.json"
)


class SEWSGlobalCausalGraphGenerator:
    def __init__(self, db: Client):
        self.db = db

    @staticmethod
    def _key(*parts: str) -> str:
        raw = "|".join(parts)
        digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return digest.upper()

    @staticmethod
    def _node_key(problem_key: str, role: str) -> str:
        return f"{problem_key}-NODE-{role}".upper()

    @staticmethod
    def _edge_key(
        problem_key: str,
        parent_role: str,
        child_role: str,
    ) -> str:
        return (
            f"{problem_key}-EDGE-{parent_role}-{child_role}"
        ).upper()

    @staticmethod
    def _node_templates(
        problem: dict[str, Any],
    ) -> list[dict[str, Any]]:
        horizon = int(problem.get("horizon_days") or 90)
        base_rate = float(problem.get("base_rate") or 0.1)

        return [
            {
                "role": "STRUCTURAL_CONDITION",
                "name": "Structural Conditions",
                "description": (
                    "Persistent geopolitical, economic, institutional, "
                    "military, environmental, or social conditions that "
                    "shape the warning environment."
                ),
                "node_type": "CONDITION",
                "prior_probability": min(
                    0.95,
                    max(0.05, base_rate * 1.25),
                ),
                "sequence_order": 10,
                "decay_half_life_hours": max(
                    336,
                    horizon * 24,
                ),
            },
            {
                "role": "PRECURSOR_ACTIVITY",
                "name": "Precursor Activity",
                "description": (
                    "Observable preparatory actions or emerging signals "
                    "consistent with the warning hypothesis."
                ),
                "node_type": "ACTION",
                "prior_probability": min(
                    0.9,
                    max(0.03, base_rate),
                ),
                "sequence_order": 20,
                "decay_half_life_hours": 336,
            },
            {
                "role": "ACCELERATION",
                "name": "Acceleration",
                "description": (
                    "Evidence that the risk trajectory is intensifying "
                    "or moving more quickly toward realization."
                ),
                "node_type": "INTERMEDIATE_EFFECT",
                "prior_probability": min(
                    0.8,
                    max(0.02, base_rate * 0.8),
                ),
                "sequence_order": 30,
                "decay_half_life_hours": 168,
            },
            {
                "role": "TRIGGER_EVENT",
                "name": "Trigger Event",
                "description": (
                    "A discrete event capable of moving the warning "
                    "problem into immediate escalation."
                ),
                "node_type": "EVENT",
                "prior_probability": min(
                    0.7,
                    max(0.01, base_rate * 0.6),
                ),
                "sequence_order": 40,
                "decay_half_life_hours": 72,
            },
            {
                "role": "TRANSMISSION",
                "name": "Transmission and Propagation",
                "description": (
                    "The mechanism through which the trigger spreads "
                    "across sectors, geography, institutions, markets, "
                    "or operational systems."
                ),
                "node_type": "INTERMEDIATE_EFFECT",
                "prior_probability": min(
                    0.65,
                    max(0.01, base_rate * 0.5),
                ),
                "sequence_order": 50,
                "decay_half_life_hours": 168,
            },
            {
                "role": "OUTCOME",
                "name": problem["title"],
                "description": problem["hypothesis"],
                "node_type": "OUTCOME",
                "prior_probability": base_rate,
                "sequence_order": 60,
                "decay_half_life_hours": max(
                    168,
                    horizon * 12,
                ),
            },
            {
                "role": "MITIGATION",
                "name": "Mitigation and Restraint",
                "description": (
                    "Diplomatic, institutional, military, economic, "
                    "operational, environmental, or social factors that "
                    "reduce the probability of the warning outcome."
                ),
                "node_type": "MITIGATOR",
                "prior_probability": 0.2,
                "sequence_order": 25,
                "decay_half_life_hours": 168,
            },
        ]

    @staticmethod
    def _edge_templates(
        problem: dict[str, Any],
    ) -> list[dict[str, Any]]:
        domain = str(problem.get("domain") or "").lower()

        domain_strength = {
            "conflict and military": 0.78,
            "energy and supply chain": 0.74,
            "economic and financial": 0.68,
            "political stability": 0.66,
            "cyber and information operations": 0.72,
            "humanitarian and public health": 0.67,
            "climate and environmental": 0.64,
            "corporate and strategic exposure": 0.62,
        }.get(domain, 0.65)

        return [
            {
                "parent": "STRUCTURAL_CONDITION",
                "child": "PRECURSOR_ACTIVITY",
                "relationship_type": "ENABLES",
                "transmission_strength": 0.65,
                "conditional_probability": 0.6,
                "lag_hours": 168,
            },
            {
                "parent": "PRECURSOR_ACTIVITY",
                "child": "ACCELERATION",
                "relationship_type": "INCREASES",
                "transmission_strength": domain_strength,
                "conditional_probability": 0.68,
                "lag_hours": 72,
            },
            {
                "parent": "ACCELERATION",
                "child": "TRIGGER_EVENT",
                "relationship_type": "TRIGGERS",
                "transmission_strength": domain_strength,
                "conditional_probability": 0.62,
                "lag_hours": 24,
            },
            {
                "parent": "TRIGGER_EVENT",
                "child": "TRANSMISSION",
                "relationship_type": "TRANSMITS",
                "transmission_strength": 0.75,
                "conditional_probability": 0.7,
                "lag_hours": 24,
            },
            {
                "parent": "TRANSMISSION",
                "child": "OUTCOME",
                "relationship_type": "INCREASES",
                "transmission_strength": 0.8,
                "conditional_probability": 0.74,
                "lag_hours": 48,
            },
            {
                "parent": "MITIGATION",
                "child": "ACCELERATION",
                "relationship_type": "MITIGATES",
                "transmission_strength": 0.55,
                "conditional_probability": 0.5,
                "lag_hours": 24,
            },
            {
                "parent": "MITIGATION",
                "child": "OUTCOME",
                "relationship_type": "INHIBITS",
                "transmission_strength": 0.6,
                "conditional_probability": 0.55,
                "lag_hours": 24,
            },
        ]

    def generate_all(self) -> dict[str, Any]:
        registry = json.loads(REGISTRY_PATH.read_text())
        problems = registry.get("warning_problems") or []

        active = [
            problem
            for problem in problems
            if problem.get("active", True)
        ]

        totals = {
            "warning_problems": 0,
            "nodes_created": 0,
            "edges_created": 0,
        }

        for problem in active:
            problem_key = problem["problem_key"]

            node_ids: dict[str, str] = {}

            for template in self._node_templates(problem):
                role = template["role"]
                row = {
                    "node_key": self._node_key(
                        problem_key,
                        role,
                    ),
                    "problem_key": problem_key,
                    "name": template["name"],
                    "description": template["description"],
                    "node_type": template["node_type"],
                    "prior_probability": template[
                        "prior_probability"
                    ],
                    "current_probability": template[
                        "prior_probability"
                    ],
                    "confidence": 0,
                    "decay_half_life_hours": template[
                        "decay_half_life_hours"
                    ],
                    "sequence_order": template[
                        "sequence_order"
                    ],
                    "active": True,
                    "metadata": {
                        "domain": problem.get("domain"),
                        "region": problem.get("region"),
                        "countries": problem.get("countries"),
                        "horizon_days": problem.get(
                            "horizon_days"
                        ),
                        "generator_version": (
                            "sews-global-causal-generator-v1"
                        ),
                    },
                }

                result = (
                    self.db.table("sews_causal_nodes")
                    .upsert(
                        row,
                        on_conflict="node_key",
                    )
                    .execute()
                )

                saved = result.data[0]
                node_ids[role] = str(saved["id"])
                totals["nodes_created"] += 1

            for template in self._edge_templates(problem):
                parent = template["parent"]
                child = template["child"]

                row = {
                    "edge_key": self._edge_key(
                        problem_key,
                        parent,
                        child,
                    ),
                    "problem_key": problem_key,
                    "parent_node_id": node_ids[parent],
                    "child_node_id": node_ids[child],
                    "relationship_type": template[
                        "relationship_type"
                    ],
                    "transmission_strength": template[
                        "transmission_strength"
                    ],
                    "conditional_probability": template[
                        "conditional_probability"
                    ],
                    "lag_hours": template["lag_hours"],
                    "active": True,
                    "rationale": (
                        f"Global causal template for "
                        f"{problem['title']}."
                    ),
                    "metadata": {
                        "generator_version": (
                            "sews-global-causal-generator-v1"
                        )
                    },
                }

                (
                    self.db.table("sews_causal_edges")
                    .upsert(
                        row,
                        on_conflict="edge_key",
                    )
                    .execute()
                )

                totals["edges_created"] += 1

            totals["warning_problems"] += 1

        return totals
