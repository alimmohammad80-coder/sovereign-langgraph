from __future__ import annotations

from statistics import mean
from typing import Any

from supabase import Client

from app.services.sews_causal_propagation_service import (
    SEWSCausalPropagationService,
)


RUNNER_VERSION = "sews-causal-propagation-runner-v1"


class SEWSCausalPropagationRunner:
    """Run causal propagation for every active SEWS warning problem."""

    def __init__(self, db: Client):
        self.db = db

    def _active_problem_keys(self) -> list[str]:
        rows = (
            self.db.table("sews_warning_problems")
            .select("problem_key")
            .eq("active", True)
            .order("problem_key")
            .range(0, 4999)
            .execute()
            .data
            or []
        )

        return [
            str(row["problem_key"])
            for row in rows
            if row.get("problem_key")
        ]

    def run_all(self, *, persist: bool = True) -> dict[str, Any]:
        problem_keys = self._active_problem_keys()
        service = SEWSCausalPropagationService(self.db)

        results: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []

        for problem_key in problem_keys:
            try:
                result = service.propagate(
                    problem_key,
                    persist=persist,
                )

                results.append(
                    {
                        "problem_key": problem_key,
                        "outcome_probability": float(
                            result["outcome_probability"]
                        ),
                        "confidence_score": float(
                            result["confidence_score"]
                        ),
                        "causal_assessment_id": result.get(
                            "causal_assessment_id"
                        ),
                        "formula_version": result.get(
                            "formula_version"
                        ),
                    }
                )

                print(
                    f"✅ {problem_key}: "
                    f"p={result['outcome_probability']:.4f} "
                    f"confidence={result['confidence_score']:.2f}"
                )

            except Exception as exc:
                error = {
                    "problem_key": problem_key,
                    "error": f"{type(exc).__name__}: {exc}",
                }
                errors.append(error)
                print(
                    f"❌ {problem_key}: "
                    f"{error['error']}"
                )

        probabilities = [
            item["outcome_probability"]
            for item in results
        ]
        confidences = [
            item["confidence_score"]
            for item in results
        ]

        return {
            "runner_version": RUNNER_VERSION,
            "persist": persist,
            "warning_problems_processed": len(problem_keys),
            "successful_propagations": len(results),
            "failed_propagations": len(errors),
            "average_outcome_probability": round(
                mean(probabilities),
                6,
            ) if probabilities else None,
            "average_confidence_score": round(
                mean(confidences),
                2,
            ) if confidences else None,
            "minimum_confidence_score": round(
                min(confidences),
                2,
            ) if confidences else None,
            "maximum_confidence_score": round(
                max(confidences),
                2,
            ) if confidences else None,
            "results": results,
            "errors": errors,
        }
