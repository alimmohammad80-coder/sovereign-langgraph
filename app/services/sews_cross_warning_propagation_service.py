from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from supabase import Client


FORMULA_VERSION = "sews-cross-warning-propagation-v1.0.0"


class SEWSCrossWarningPropagationError(RuntimeError):
    pass


class SEWSCrossWarningPropagationService:
    def __init__(self, db: Client):
        self.db = db

    @staticmethod
    def _bounded(value: float) -> float:
        return max(0.0, min(1.0, value))

    def _latest_causal_assessments(self) -> dict[str, dict[str, Any]]:
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
            key = row["problem_key"]
            if key not in latest:
                latest[key] = row

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

    def propagate(
        self,
        *,
        persist: bool = True,
    ) -> dict[str, Any]:
        assessments = self._latest_causal_assessments()
        dependencies = self._dependencies()

        if not dependencies:
            raise SEWSCrossWarningPropagationError(
                "No validated cross-warning dependencies found."
            )

        updates: list[dict[str, Any]] = []
        skipped = 0

        for dependency in dependencies:
            source_key = dependency["source_problem_key"]
            target_key = dependency["target_problem_key"]

            source = assessments.get(source_key)
            target = assessments.get(target_key)

            if not source or not target:
                skipped += 1
                continue

            source_probability = float(
                source["outcome_probability"]
            )
            target_probability = float(
                target["outcome_probability"]
            )

            strength = float(
                dependency["transmission_strength"]
            )
            conditional = float(
                dependency["conditional_probability"]
                or 0
            )
            lag_hours = int(
                dependency.get("lag_hours") or 0
            )

            source_time = datetime.fromisoformat(
                str(source["assessed_at"]).replace(
                    "Z",
                    "+00:00",
                )
            )

            eligible_at = source_time + timedelta(
                hours=lag_hours
            )

            now = datetime.now(timezone.utc)

            if now < eligible_at:
                skipped += 1
                continue

            transmitted = self._bounded(
                source_probability
                * strength
                * conditional
            )

            relationship_type = dependency[
                "relationship_type"
            ]

            if relationship_type in {
                "MITIGATES",
                "INHIBITS",
            }:
                adjusted = self._bounded(
                    target_probability
                    - transmitted * target_probability
                )
            else:
                adjusted = self._bounded(
                    target_probability
                    + transmitted * (
                        1.0 - target_probability
                    )
                )

            updates.append(
                {
                    "dependency_id": dependency["id"],
                    "dependency_key": dependency[
                        "dependency_key"
                    ],
                    "source_problem_key": source_key,
                    "target_problem_key": target_key,
                    "relationship_type": relationship_type,
                    "source_probability": round(
                        source_probability,
                        6,
                    ),
                    "target_probability_before": round(
                        target_probability,
                        6,
                    ),
                    "transmitted_effect": round(
                        transmitted,
                        6,
                    ),
                    "target_probability_after": round(
                        adjusted,
                        6,
                    ),
                    "transmission_strength": strength,
                    "conditional_probability": conditional,
                    "lag_hours": lag_hours,
                    "formula_version": FORMULA_VERSION,
                }
            )

        if persist and updates:
            for item in updates:
                (
                    self.db.table(
                        "sews_cross_warning_propagation_runs"
                    )
                    .insert(
                        {
                            **item,
                            "created_at": datetime.now(
                                timezone.utc
                            ).isoformat(),
                        }
                    )
                    .execute()
                )

        return {
            "relationships_considered": len(
                dependencies
            ),
            "propagations_created": len(updates),
            "propagations_skipped": skipped,
            "updates": updates,
            "formula_version": FORMULA_VERSION,
        }
