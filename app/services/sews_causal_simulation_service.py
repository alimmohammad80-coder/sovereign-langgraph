from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any

from supabase import Client


FORMULA_VERSION = "sews-causal-simulation-v1.0.0"


class SEWSCausalSimulationError(RuntimeError):
    pass


class SEWSCausalSimulationService:
    def __init__(self, db: Client):
        self.db = db

    @staticmethod
    def _bounded(value: float) -> float:
        return max(0.0, min(1.0, value))

    def _latest_assessments(self) -> dict[str, dict[str, Any]]:
        rows = (
            self.db.table("sews_causal_assessments")
            .select(
                "id,problem_key,outcome_probability,"
                "confidence_score,assessed_at"
            )
            .order("assessed_at", desc=True)
            .range(0, 4999)
            .execute()
            .data
            or []
        )

        latest: dict[str, dict[str, Any]] = {}

        for row in rows:
            latest.setdefault(row["problem_key"], row)

        return latest

    def _dependencies(self) -> list[dict[str, Any]]:
        return (
            self.db.table("sews_warning_dependencies")
            .select("*")
            .eq("active", True)
            .eq("direction_status", "VALIDATED")
            .neq("relationship_type", "RELATED")
            .execute()
            .data
            or []
        )

    def simulate(
        self,
        *,
        problem_key: str,
        max_depth: int = 5,
        ignore_lags: bool = True,
        persist: bool = False,
    ) -> dict[str, Any]:
        assessments = self._latest_assessments()

        if problem_key not in assessments:
            raise SEWSCausalSimulationError(
                f"No causal assessment exists for {problem_key}."
            )

        dependencies = self._dependencies()
        outgoing: dict[str, list[dict[str, Any]]] = {}

        for dependency in dependencies:
            outgoing.setdefault(
                dependency["source_problem_key"],
                [],
            ).append(dependency)

        simulated_probabilities = {
            key: float(row["outcome_probability"])
            for key, row in assessments.items()
        }

        simulated_confidences = {
            key: float(row.get("confidence_score") or 0)
            for key, row in assessments.items()
        }

        queue = deque([(problem_key, 0)])
        visited_depth: dict[str, int] = {problem_key: 0}
        traversed_edges: set[str] = set()
        propagation_tree: list[dict[str, Any]] = []
        now = datetime.now(timezone.utc)

        while queue:
            source_key, depth = queue.popleft()

            if depth >= max_depth:
                continue

            for dependency in outgoing.get(source_key, []):
                dependency_id = str(dependency["id"])

                if dependency_id in traversed_edges:
                    continue

                traversed_edges.add(dependency_id)

                target_key = dependency["target_problem_key"]

                if target_key not in simulated_probabilities:
                    continue

                source_assessment = assessments[source_key]
                source_time = datetime.fromisoformat(
                    str(source_assessment["assessed_at"]).replace(
                        "Z",
                        "+00:00",
                    )
                )

                lag_hours = int(dependency.get("lag_hours") or 0)
                eligible_at = source_time + timedelta(hours=lag_hours)

                if not ignore_lags and now < eligible_at:
                    continue

                source_probability = simulated_probabilities[source_key]
                target_before = simulated_probabilities[target_key]

                strength = float(
                    dependency.get("transmission_strength") or 0
                )
                conditional = float(
                    dependency.get("conditional_probability") or 0
                )

                transmitted_effect = self._bounded(
                    source_probability * strength * conditional
                )

                relationship_type = dependency["relationship_type"]

                if relationship_type in {"MITIGATES", "INHIBITS"}:
                    target_after = self._bounded(
                        target_before
                        - transmitted_effect * target_before
                    )
                else:
                    target_after = self._bounded(
                        target_before
                        + transmitted_effect * (1.0 - target_before)
                    )

                confidence_before = float(
                    simulated_confidences.get(target_key)
                    or assessments[target_key].get("confidence_score")
                    or 50.0
                )

                source_confidence = float(
                    simulated_confidences.get(source_key)
                    or assessments[source_key].get("confidence_score")
                    or 50.0
                )

                validation_multiplier = 1.0
                status = str(
                    dependency.get("direction_status") or ""
                ).upper()

                if status == "VALIDATED":
                    validation_multiplier = 1.0
                elif status == "PARTIALLY_VALIDATED":
                    validation_multiplier = 0.85
                else:
                    validation_multiplier = 0.70

                propagated_confidence = (
                    source_confidence
                    * max(0.25, strength)
                    * max(0.25, conditional)
                    * validation_multiplier
                )

                confidence_after = round(
                    min(
                        100.0,
                        max(confidence_before, propagated_confidence),
                    ),
                    2,
                )

                simulated_confidences[target_key] = confidence_after

                simulated_probabilities[target_key] = target_after
                simulated_confidences[target_key] = confidence_after

                propagation_tree.append(
                    {
                        "depth": depth + 1,
                        "source_problem_key": source_key,
                        "target_problem_key": target_key,
                        "relationship_type": relationship_type,
                        "transmission_strength": strength,
                        "conditional_probability": conditional,
                        "lag_hours": lag_hours,
                        "lag_ignored": ignore_lags,
                        "source_probability": round(
                            source_probability,
                            6,
                        ),
                        "target_probability_before": round(
                            target_before,
                            6,
                        ),
                        "transmitted_effect": round(
                            transmitted_effect,
                            6,
                        ),
                        "target_probability_after": round(
                            target_after,
                            6,
                        ),
                        "confidence_before": round(
                            confidence_before,
                            2,
                        ),
                        "confidence_after": round(
                            confidence_after,
                            2,
                        ),
                        "rationale": dependency.get("rationale"),
                    }
                )

                next_depth = depth + 1

                if (
                    next_depth < max_depth
                    and (
                        target_key not in visited_depth
                        or next_depth < visited_depth[target_key]
                    )
                ):
                    visited_depth[target_key] = next_depth
                    queue.append((target_key, next_depth))

        affected = []

        for key, probability_after in simulated_probabilities.items():
            probability_before = float(
                assessments[key]["outcome_probability"]
            )
            change = probability_after - probability_before

            if abs(change) < 0.000001:
                continue

            affected.append(
                {
                    "problem_key": key,
                    "probability_before": round(
                        probability_before,
                        6,
                    ),
                    "probability_after": round(
                        probability_after,
                        6,
                    ),
                    "probability_change": round(change, 6),
                    "confidence_after": round(
                        simulated_confidences[key],
                        2,
                    ),
                }
            )

        affected.sort(
            key=lambda item: abs(item["probability_change"]),
            reverse=True,
        )

        highest_risk = max(
            affected,
            key=lambda item: item["probability_after"],
            default=None,
        )

        largest_change = affected[0] if affected else None

        result = {
            "root_problem": problem_key,
            "simulation": True,
            "ignore_lags": ignore_lags,
            "max_depth": max_depth,
            "nodes_visited": len(visited_depth),
            "edges_traversed": len(propagation_tree),
            "propagation_tree": propagation_tree,
            "affected_warning_problems": affected,
            "overall_system_impact": {
                "highest_risk_problem": highest_risk,
                "largest_probability_change": largest_change,
            },
            "formula_version": FORMULA_VERSION,
        }

        if persist:
            result["persistence"] = (
                "Simulation persistence is disabled in v1."
            )

        return result
