from __future__ import annotations

from typing import Any

from supabase import Client


class SEWSWarningBaselineService:
    def __init__(self, db: Client):
        self.db = db

    def _warning_problems(self) -> list[dict[str, Any]]:
        return (
            self.db.table("sews_warning_problems")
            .select(
                "id,problem_key,title,hypothesis,"
                "horizon_days,severity_score,exposure_map"
            )
            .eq("active", True)
            .order("problem_key")
            .range(0, 4999)
            .execute()
            .data
            or []
        )

    @staticmethod
    def _build_baseline(problem: dict[str, Any]) -> dict[str, Any]:
        title = str(problem.get("title") or "")
        hypothesis = str(problem.get("hypothesis") or "")
        exposure = problem.get("exposure_map") or {}
        classification = exposure.get("classification") or {}

        region = (
            exposure.get("region")
            or classification.get("region")
            or classification.get("region_key")
            or "Global"
        )

        domain = (
            classification.get("primary_domain")
            or "Strategic Warning"
        )

        strategic_context = (
            f"{title} is monitored as a standing SEWS warning problem "
            f"within the {domain} domain for {region}. "
            f"The warning hypothesis is: {hypothesis}"
        )

        why_it_matters = (
            f"A material deterioration in {title.lower()} could affect "
            f"regional stability, government decision-making, economic "
            f"activity, security conditions, and related warning problems. "
            f"SEWS therefore maintains this issue as a persistent strategic "
            f"watch item."
        )

        structural_drivers = [
            "Underlying political and security conditions",
            "State and non-state actor behavior",
            "Economic and institutional pressure",
            "Regional and international involvement",
        ]

        escalation_pathways = [
            "Sustained deterioration in relevant warning indicators",
            "A discrete trigger or shock changes actor behavior",
            "Escalatory actions produce reciprocal responses",
            "Regional spillover broadens the scope of the warning",
        ]

        historical_analogs = [
            {
                "name": "Historical comparison pending",
                "lesson": (
                    "SEWS will attach validated historical analogs "
                    "as the evidence base develops."
                ),
            }
        ]

        monitoring_priorities = [
            "Material changes in active indicators",
            "New corroborated evidence from trusted sources",
            "Changes in official or actor behavior",
            "Cross-warning propagation and regional spillover",
        ]

        return {
            "warning_problem_id": problem["id"],
            "strategic_context": strategic_context,
            "why_it_matters": why_it_matters,
            "structural_drivers": structural_drivers,
            "escalation_pathways": escalation_pathways,
            "historical_analogs": historical_analogs,
            "monitoring_priorities": monitoring_priorities,
            "metadata": {
                "problem_key": problem.get("problem_key"),
                "region": region,
                "domain": domain,
                "baseline_version": "sews-warning-baseline-v1",
            },
        }

    def seed_all(self, *, force: bool = False) -> dict[str, Any]:
        problems = self._warning_problems()

        existing_rows = (
            self.db.table("sews_warning_baselines")
            .select("warning_problem_id")
            .range(0, 4999)
            .execute()
            .data
            or []
        )

        existing_ids = {
            str(row["warning_problem_id"])
            for row in existing_rows
            if row.get("warning_problem_id")
        }

        inserted = 0
        updated = 0
        skipped = 0
        errors: list[dict[str, str]] = []

        for problem in problems:
            problem_id = str(problem["id"])
            baseline = self._build_baseline(problem)

            try:
                if problem_id in existing_ids:
                    if not force:
                        skipped += 1
                        continue

                    (
                        self.db.table("sews_warning_baselines")
                        .update(baseline)
                        .eq("warning_problem_id", problem_id)
                        .execute()
                    )
                    updated += 1
                else:
                    (
                        self.db.table("sews_warning_baselines")
                        .insert(baseline)
                        .execute()
                    )
                    inserted += 1
            except Exception as exc:
                errors.append(
                    {
                        "problem_key": str(problem.get("problem_key")),
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )

        return {
            "status": "success" if not errors else "partial",
            "warning_problems_found": len(problems),
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
            "errors": errors,
        }
