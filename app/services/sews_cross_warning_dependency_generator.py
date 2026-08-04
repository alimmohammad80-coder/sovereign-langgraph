from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from supabase import Client


REGISTRY_PATH = Path(
    "app/data/sews_global_warning_registry.json"
)


class SEWSCrossWarningDependencyGenerator:
    def __init__(self, db: Client):
        self.db = db

    @staticmethod
    def _canonical_pair(
        first: str,
        second: str,
    ) -> tuple[str, str]:
        return tuple(sorted((first, second)))

    @staticmethod
    def _dependency_key(
        source: str,
        target: str,
    ) -> str:
        raw = f"{source}|{target}|RELATED"
        digest = hashlib.sha256(
            raw.encode()
        ).hexdigest()[:16]

        return f"SEWS-DEP-{digest}".upper()

    def generate_all(self) -> dict[str, Any]:
        registry = json.loads(
            REGISTRY_PATH.read_text()
        )

        problems = registry.get(
            "warning_problems"
        ) or []

        valid_keys = {
            problem["problem_key"]
            for problem in problems
            if problem.get("active", True)
        }

        seen: set[tuple[str, str]] = set()
        created = 0
        skipped = 0

        for problem in problems:
            source_key = problem["problem_key"]

            dependencies = (
                problem.get("dependencies")
                or {}
            )

            related = dependencies.get(
                "related_warning_problems"
            ) or []

            for target_key in related:
                if target_key not in valid_keys:
                    skipped += 1
                    continue

                source, target = self._canonical_pair(
                    source_key,
                    target_key,
                )

                pair = (source, target)

                if pair in seen:
                    continue

                seen.add(pair)

                row = {
                    "dependency_key": (
                        self._dependency_key(
                            source,
                            target,
                        )
                    ),
                    "source_problem_key": source,
                    "target_problem_key": target,
                    "relationship_type": "RELATED",
                    "direction_status": "UNVALIDATED",
                    "transmission_strength": 0,
                    "conditional_probability": None,
                    "lag_hours": 0,
                    "rationale": (
                        "Relationship imported from the "
                        "global SEWS warning registry. "
                        "Direction and causal strength have "
                        "not yet been analytically validated."
                    ),
                    "active": True,
                    "metadata": {
                        "generator_version": (
                            "sews-cross-warning-generator-v1"
                        ),
                        "registry_version": registry.get(
                            "registry_version"
                        ),
                    },
                }

                (
                    self.db.table(
                        "sews_warning_dependencies"
                    )
                    .upsert(
                        row,
                        on_conflict="dependency_key",
                    )
                    .execute()
                )

                created += 1

        return {
            "warning_problems_considered": len(
                valid_keys
            ),
            "relationships_created": created,
            "relationships_skipped": skipped,
        }
