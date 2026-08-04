from __future__ import annotations

import math
from datetime import datetime, timezone
from statistics import mean
from typing import Any

from supabase import Client


FORMULA_VERSION = "sews-causal-propagation-v1.0.0"


class SEWSCausalPropagationError(RuntimeError):
    pass


class SEWSCausalPropagationService:
    def __init__(self, db: Client):
        self.db = db

    @staticmethod
    def _bounded(value: float) -> float:
        return max(0.0, min(1.0, value))

    @staticmethod
    def _combine_probabilities(values: list[float]) -> float:
        if not values:
            return 0.0

        remaining = 1.0
        for value in values:
            remaining *= 1.0 - max(0.0, min(1.0, value))

        return 1.0 - remaining

    def _nodes(self, problem_key: str) -> list[dict[str, Any]]:
        return (
            self.db.table("sews_causal_nodes")
            .select("*")
            .eq("problem_key", problem_key)
            .eq("active", True)
            .order("sequence_order")
            .execute()
            .data
            or []
        )

    def _edges(self, problem_key: str) -> list[dict[str, Any]]:
        return (
            self.db.table("sews_causal_edges")
            .select("*")
            .eq("problem_key", problem_key)
            .eq("active", True)
            .execute()
            .data
            or []
        )

    def _links(self, node_ids: list[str]) -> list[dict[str, Any]]:
        if not node_ids:
            return []

        return (
            self.db.table("sews_causal_node_indicator_links")
            .select("*")
            .in_("node_id", node_ids)
            .eq("active", True)
            .execute()
            .data
            or []
        )

    def _indicator_states(
        self,
        indicator_keys: list[str],
    ) -> dict[str, dict[str, Any]]:
        if not indicator_keys:
            return {}

        rows = (
            self.db.table("sews_indicator_state")
            .select(
                "indicator_key,current_value,confidence,"
                "status,freshness_score,updated_at"
            )
            .in_("indicator_key", indicator_keys)
            .execute()
            .data
            or []
        )

        return {
            row["indicator_key"]: row
            for row in rows
        }

    def _latest_warning_assessment(
        self,
        problem_key: str,
    ) -> dict[str, Any] | None:
        warning = (
            self.db.table("sews_warning_problems")
            .select("id")
            .eq("problem_key", problem_key)
            .limit(1)
            .execute()
            .data
            or []
        )

        if not warning:
            return None

        rows = (
            self.db.table("sews_assessments")
            .select("id,probability,confidence_score,assessed_at")
            .eq("warning_problem_id", warning[0]["id"])
            .order("assessed_at", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )

        return rows[0] if rows else None

    def propagate(
        self,
        problem_key: str,
        *,
        persist: bool = True,
    ) -> dict[str, Any]:
        nodes = self._nodes(problem_key)
        edges = self._edges(problem_key)

        if not nodes:
            raise SEWSCausalPropagationError(
                f"No causal nodes for {problem_key}."
            )

        node_by_id = {
            str(node["id"]): node
            for node in nodes
        }

        links = self._links(list(node_by_id))
        links_by_node: dict[str, list[dict[str, Any]]] = {}

        for link in links:
            links_by_node.setdefault(
                str(link["node_id"]),
                [],
            ).append(link)

        indicator_keys = list(
            {
                link["indicator_key"]
                for link in links
            }
        )

        states = self._indicator_states(indicator_keys)

        probabilities: dict[str, float] = {}
        confidences: dict[str, float] = {}
        explanations: list[dict[str, Any]] = []

        for node in nodes:
            node_id = str(node["id"])
            prior = float(node.get("prior_probability") or 0.1)
            node_links = links_by_node.get(node_id, [])

            positive_signals: list[float] = []
            negative_signals: list[float] = []
            link_confidences: list[float] = []
            indicator_details: list[dict[str, Any]] = []

            for link in node_links:
                state = states.get(link["indicator_key"])

                if not state or state.get("current_value") is None:
                    continue

                value = float(state["current_value"])
                confidence = float(state.get("confidence") or 0) / 100
                freshness = (
                    float(state.get("freshness_score") or 0) / 100
                )
                weight = float(link.get("influence_weight") or 1.0)

                effective = self._bounded(
                    value
                    * confidence
                    * max(0.05, freshness)
                    * min(1.0, weight)
                )

                if link["influence_type"] == "CONTRADICTING":
                    negative_signals.append(effective)
                else:
                    positive_signals.append(effective)

                link_confidences.append(confidence)

                indicator_details.append(
                    {
                        "indicator_key": link["indicator_key"],
                        "influence_type": link["influence_type"],
                        "effective_strength": round(effective, 6),
                        "confidence": round(confidence * 100, 2),
                        "freshness": round(freshness * 100, 2),
                    }
                )

            positive = self._combine_probabilities(
                positive_signals
            )
            negative = self._combine_probabilities(
                negative_signals
            )

            local_probability = self._bounded(
                prior
                + positive * (1.0 - prior)
                - negative * prior
            )

            probabilities[node_id] = local_probability
            confidences[node_id] = (
                mean(link_confidences) * 100
                if link_confidences
                else float(node.get("confidence") or 0)
            )

            explanations.append(
                {
                    "node_key": node["node_key"],
                    "node_name": node["name"],
                    "prior_probability": round(prior, 6),
                    "local_probability": round(
                        local_probability,
                        6,
                    ),
                    "supporting_signal": round(positive, 6),
                    "contradicting_signal": round(
                        negative,
                        6,
                    ),
                    "indicators": indicator_details,
                }
            )

        incoming: dict[str, list[dict[str, Any]]] = {}

        for edge in edges:
            incoming.setdefault(
                str(edge["child_node_id"]),
                [],
            ).append(edge)

        for node in nodes:
            node_id = str(node["id"])
            parent_effects: list[float] = []
            mitigating_effects: list[float] = []

            for edge in incoming.get(node_id, []):
                parent_probability = probabilities.get(
                    str(edge["parent_node_id"]),
                    0.0,
                )

                effect = self._bounded(
                    parent_probability
                    * float(edge["transmission_strength"])
                    * float(edge["conditional_probability"])
                )

                if edge["relationship_type"] in {
                    "MITIGATES",
                    "INHIBITS",
                }:
                    mitigating_effects.append(effect)
                else:
                    parent_effects.append(effect)

            propagated_support = self._combine_probabilities(
                parent_effects
            )
            propagated_mitigation = self._combine_probabilities(
                mitigating_effects
            )

            current = probabilities[node_id]

            current = self._bounded(
                current
                + propagated_support * (1.0 - current)
                - propagated_mitigation * current
            )

            probabilities[node_id] = current

        node_snapshot = []

        for node in nodes:
            node_id = str(node["id"])

            node_snapshot.append(
                {
                    "node_id": node_id,
                    "node_key": node["node_key"],
                    "name": node["name"],
                    "node_type": node["node_type"],
                    "sequence_order": node["sequence_order"],
                    "probability": round(
                        probabilities[node_id],
                        6,
                    ),
                    "confidence": round(
                        confidences[node_id],
                        2,
                    ),
                }
            )

            if persist:
                (
                    self.db.table("sews_causal_nodes")
                    .update(
                        {
                            "current_probability": round(
                                probabilities[node_id],
                                6,
                            ),
                            "confidence": round(
                                confidences[node_id],
                                2,
                            ),
                            "updated_at": datetime.now(
                                timezone.utc
                            ).isoformat(),
                        }
                    )
                    .eq("id", node_id)
                    .execute()
                )

        outcome_nodes = [
            node
            for node in nodes
            if node["node_type"] == "OUTCOME"
        ]

        if not outcome_nodes:
            raise SEWSCausalPropagationError(
                f"No OUTCOME node for {problem_key}."
            )

        outcome_node = outcome_nodes[0]
        outcome_probability = probabilities[
            str(outcome_node["id"])
        ]

        warning_assessment = self._latest_warning_assessment(
            problem_key
        )

        useful_confidences = [
            value
            for value in confidences.values()
            if value > 0
        ]

        confidence_score = (
            mean(useful_confidences)
            if useful_confidences
            else 0.0
        )

        root_probability = float(
            nodes[0].get("prior_probability") or 0.1
        )

        result = {
            "problem_key": problem_key,
            "root_probability": round(root_probability, 6),
            "outcome_probability": round(
                outcome_probability,
                6,
            ),
            "confidence_score": round(
                confidence_score,
                2,
            ),
            "node_snapshot": node_snapshot,
            "edge_snapshot": edges,
            "explanation": {
                "node_explanations": explanations,
                "warning_assessment_probability": (
                    warning_assessment.get("probability")
                    if warning_assessment
                    else None
                ),
                "formula_version": FORMULA_VERSION,
            },
            "formula_version": FORMULA_VERSION,
        }

        if persist:
            row = {
                "problem_key": problem_key,
                "warning_assessment_id": (
                    warning_assessment.get("id")
                    if warning_assessment
                    else None
                ),
                "assessed_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "root_probability": result[
                    "root_probability"
                ],
                "outcome_probability": result[
                    "outcome_probability"
                ],
                "confidence_score": result[
                    "confidence_score"
                ],
                "node_snapshot": node_snapshot,
                "edge_snapshot": edges,
                "explanation": result["explanation"],
                "formula_version": FORMULA_VERSION,
            }

            saved = (
                self.db.table("sews_causal_assessments")
                .insert(row)
                .execute()
                .data
                or []
            )

            result["causal_assessment_id"] = (
                saved[0]["id"] if saved else None
            )

        return result
