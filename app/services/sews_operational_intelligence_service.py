from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from supabase import Client


class SEWSOperationalIntelligenceService:
    def __init__(self, db: Client):
        self.db = db

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _probability_band(value: float) -> str:
        if value < 0.20:
            return "LOW"
        if value < 0.40:
            return "ELEVATED"
        if value < 0.60:
            return "HIGH"
        if value < 0.80:
            return "VERY_HIGH"
        return "CRITICAL"

    @staticmethod
    def _latest_by_key(
        rows: list[dict[str, Any]],
        key: str,
    ) -> dict[str, dict[str, Any]]:
        latest: dict[str, dict[str, Any]] = {}

        for row in rows:
            identity = str(row.get(key) or "")
            if identity and identity not in latest:
                latest[identity] = row

        return latest

    def _warning_problems(self) -> list[dict[str, Any]]:
        return (
            self.db.table("sews_warning_problems")
            .select(
                "problem_key,title,hypothesis,horizon_days,"
                "severity_score,state,base_rate,active,exposure_map"
            )
            .eq("active", True)
            .order("problem_key")
            .range(0, 4999)
            .execute()
            .data
            or []
        )

    def _latest_causal_assessments(
        self,
    ) -> dict[str, dict[str, Any]]:
        rows = (
            self.db.table("sews_causal_assessments")
            .select(
                "id,problem_key,outcome_probability,"
                "confidence_score,assessed_at,formula_version"
            )
            .order("assessed_at", desc=True)
            .range(0, 9999)
            .execute()
            .data
            or []
        )

        return self._latest_by_key(rows, "problem_key")

    def _previous_causal_assessments(
        self,
    ) -> dict[str, dict[str, Any]]:
        rows = (
            self.db.table("sews_causal_assessments")
            .select(
                "id,problem_key,outcome_probability,"
                "confidence_score,assessed_at"
            )
            .order("assessed_at", desc=True)
            .range(0, 9999)
            .execute()
            .data
            or []
        )

        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for row in rows:
            grouped[str(row["problem_key"])].append(row)

        return {
            key: values[1]
            for key, values in grouped.items()
            if len(values) > 1
        }

    def _latest_products(
        self,
    ) -> dict[str, dict[str, Any]]:
        rows = (
            self.db.table(
                "sews_latest_operational_products"
            )
            .select(
                "id,warning_problem_key,generated_at,"
                "confidence,confidence_status,"
                "raw_confidence,trend,bluf,key_drivers,"
                "forecast,intelligence_gaps,"
                "collection_priorities"
            )
            .range(0, 999)
            .execute()
            .data
            or []
        )

        return self._latest_by_key(
            rows,
            "warning_problem_key",
        )

    def _recent_propagations(
        self,
        hours: int,
    ) -> list[dict[str, Any]]:
        since = (
            self._utcnow() - timedelta(hours=hours)
        ).isoformat()

        rows = (
            self.db.table(
                "sews_cross_warning_propagation_runs"
            )
            .select(
                "id,dependency_key,source_problem_key,"
                "target_problem_key,relationship_type,"
                "source_probability,target_probability_before,"
                "transmitted_effect,target_probability_after,"
                "transmission_strength,conditional_probability,"
                "lag_hours,formula_version,created_at"
            )
            .gte("created_at", since)
            .order("created_at", desc=True)
            .range(0, 999)
            .execute()
            .data
            or []
        )

        deduplicated: list[dict[str, Any]] = []
        seen: set[tuple[Any, ...]] = set()

        for row in rows:
            identity = (
                row.get("dependency_key"),
                row.get("source_problem_key"),
                row.get("target_problem_key"),
                row.get("source_probability"),
                row.get("target_probability_before"),
                row.get("target_probability_after"),
                row.get("formula_version"),
            )

            if identity in seen:
                continue

            seen.add(identity)
            deduplicated.append(row)

        return deduplicated

    def _latest_pipeline_run(self) -> dict[str, Any] | None:
        rows = (
            self.db.table("sews_pipeline_runs")
            .select(
                "id,run_key,status,started_at,finished_at,"
                "duration_seconds,warnings_updated,"
                "indicators_updated,evidence_records,"
                "propagation_events,products_generated,errors"
            )
            .order("started_at", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )

        return rows[0] if rows else None

    @staticmethod
    def _problem_region(problem: dict[str, Any]) -> str:
        exposure = problem.get("exposure_map") or {}
        return str(
            exposure.get("region")
            or exposure.get("classification", {}).get("region")
            or "Global"
        )

    @staticmethod
    def _problem_domain(problem: dict[str, Any]) -> str:
        exposure = problem.get("exposure_map") or {}
        classification = exposure.get("classification") or {}

        return str(
            classification.get("primary_domain")
            or "Strategic Warning"
        )

    def build(
        self,
        *,
        propagation_hours: int = 24,
        warning_limit: int = 12,
        product_limit: int = 8,
    ) -> dict[str, Any]:
        problems = self._warning_problems()
        latest = self._latest_causal_assessments()
        previous = self._previous_causal_assessments()
        products = self._latest_products()
        propagations = self._recent_propagations(
            propagation_hours
        )
        pipeline = self._latest_pipeline_run()

        warning_rows: list[dict[str, Any]] = []

        for problem in problems:
            problem_key = str(problem["problem_key"])
            assessment = latest.get(problem_key)

            if not assessment:
                continue

            probability = float(
                assessment.get("outcome_probability") or 0
            )
            raw_assessment_confidence = (
                assessment.get("confidence_score")
            )

            assessment_confidence = (
                round(
                    float(raw_assessment_confidence),
                    2,
                )
                if raw_assessment_confidence is not None
                else None
            )

            prior = previous.get(problem_key)
            previous_probability = (
                float(prior["outcome_probability"])
                if prior
                and prior.get("outcome_probability") is not None
                else None
            )

            probability_change = (
                probability - previous_probability
                if previous_probability is not None
                else 0.0
            )

            product = products.get(problem_key) or {}

            product_confidence = product.get("confidence")

            confidence = (
                round(
                    float(product_confidence),
                    2,
                )
                if product_confidence is not None
                else None
            )

            confidence_status = (
                product.get("confidence_status")
                or (
                    "ASSESSED"
                    if confidence is not None
                    else "INSUFFICIENT_EVIDENCE"
                )
            )

            raw_confidence = product.get(
                "raw_confidence"
            )

            if raw_confidence is None:
                raw_confidence = (
                    assessment_confidence
                )

            warning_rows.append(
                {
                    "problem_key": problem_key,
                    "title": problem.get("title"),
                    "hypothesis": problem.get("hypothesis"),
                    "region": self._problem_region(problem),
                    "domain": self._problem_domain(problem),
                    "horizon_days": problem.get("horizon_days"),
                    "severity_score": problem.get(
                        "severity_score"
                    ),
                    "official_state": problem.get("state"),
                    "probability": round(probability, 6),
                    "probability_percent": round(
                        probability * 100,
                        2,
                    ),
                    "probability_band": (
                        self._probability_band(probability)
                    ),
                    "previous_probability": (
                        round(previous_probability, 6)
                        if previous_probability is not None
                        else None
                    ),
                    "probability_change": round(
                        probability_change,
                        6,
                    ),
                    "probability_change_points": round(
                        probability_change * 100,
                        2,
                    ),
                    "confidence": confidence,
                    "raw_confidence": (
                        round(float(raw_confidence), 2)
                        if raw_confidence is not None
                        else None
                    ),
                    "confidence_status": confidence_status,
                    "trend": product.get("trend"),
                    "bluf": product.get("bluf"),
                    "key_drivers": (
                        product.get("key_drivers") or []
                    ),
                    "forecast": product.get("forecast"),
                    "intelligence_gaps": (
                        product.get("intelligence_gaps")
                        or []
                    ),
                    "collection_priorities": (
                        product.get("collection_priorities")
                        or []
                    ),
                    "assessed_at": assessment.get(
                        "assessed_at"
                    ),
                    "product_generated_at": product.get(
                        "generated_at"
                    ),
                    "product_id": product.get("id"),
                }
            )

        warning_rows.sort(
            key=lambda row: (
                row["probability"],
                row.get("severity_score") or 0,
            ),
            reverse=True,
        )

        material_changes = sorted(
            [
                row
                for row in warning_rows
                if abs(row["probability_change"]) >= 0.01
            ],
            key=lambda row: abs(
                row["probability_change"]
            ),
            reverse=True,
        )

        region_counts: dict[str, Counter] = defaultdict(
            Counter
        )

        for row in warning_rows:
            region_counts[row["region"]][
                row["probability_band"]
            ] += 1

        regional_posture = []

        for region, counts in sorted(region_counts.items()):
            regional_rows = [
                row
                for row in warning_rows
                if row["region"] == region
            ]

            regional_posture.append(
                {
                    "region": region,
                    "warning_count": len(regional_rows),
                    "highest_probability": max(
                        (
                            row["probability"]
                            for row in regional_rows
                        ),
                        default=0,
                    ),
                    "highest_risk_warning": max(
                        regional_rows,
                        key=lambda row: row["probability"],
                        default=None,
                    ),
                    "bands": dict(counts),
                }
            )

        propagation_rows = []

        for row in propagations:
            before = float(
                row.get("target_probability_before") or 0
            )
            after = float(
                row.get("target_probability_after") or 0
            )

            propagation_rows.append(
                {
                    **row,
                    "probability_change": round(
                        after - before,
                        6,
                    ),
                    "probability_change_points": round(
                        (after - before) * 100,
                        2,
                    ),
                }
            )

        product_rows = sorted(
            [
                {
                    "product_id": product.get("id"),
                    "problem_key": key,
                    "title": next(
                        (
                            problem.get("title")
                            for problem in problems
                            if problem.get("problem_key") == key
                        ),
                        key,
                    ),
                    "region": (
                        product.get("region")
                        or product.get("region_key")
                    ),
                    "country_iso3": product.get(
                        "country_iso3"
                    ),
                    "countries": (
                        product.get("countries") or []
                    ),
                    "geographic_scope": (
                        product.get("geographic_scope")
                        or {}
                    ),
                    "probability": product.get(
                        "probability"
                    ),
                    "confidence": product.get("confidence"),
                    "raw_confidence": product.get(
                        "raw_confidence"
                    ),
                    "confidence_status": (
                        product.get("confidence_status")
                        or (
                            "ASSESSED"
                            if product.get("confidence")
                            is not None
                            else "INSUFFICIENT_EVIDENCE"
                        )
                    ),
                    "trend": product.get("trend"),
                    "bluf": product.get("bluf"),
                    "executive_summary": product.get(
                        "executive_summary"
                    ),
                    "key_drivers": product.get(
                        "key_drivers"
                    )
                    or [],
                    "forecast": product.get("forecast"),
                    "generated_at": product.get(
                        "generated_at"
                    ),
                }
                for key, product in products.items()
            ],
            key=lambda row: str(
                row.get("generated_at") or ""
            ),
            reverse=True,
        )[:product_limit]

        highest = (
            warning_rows[0]
            if warning_rows
            else None
        )

        largest_change = (
            material_changes[0]
            if material_changes
            else None
        )

        if highest:
            highest_confidence = highest.get(
                "confidence"
            )

            if highest_confidence is None:
                confidence_text = (
                    "confidence not yet assessable because "
                    "the evidence base is insufficient"
                )
            else:
                confidence_text = (
                    f"{highest_confidence:.1f}% confidence"
                )

            system_bluf = (
                f"SEWS is monitoring {len(warning_rows)} active "
                f"warning problems. The highest assessed risk is "
                f"{highest['title']} at "
                f"{highest['probability_percent']:.1f}% with "
                f"{confidence_text}. "
                f"{len(material_changes)} warnings changed by at "
                f"least one percentage point, and "
                f"{len(propagation_rows)} unique cross-warning "
                f"propagation events were recorded during the last "
                f"{propagation_hours} hours."
            )
        else:
            system_bluf = (
                "No current SEWS causal assessments are available."
            )

        watch_items = []

        for row in warning_rows:
            if (
                row["probability"] >= 0.40
                or row["probability_change"] >= 0.03
            ):
                watch_items.append(
                    {
                        "problem_key": row["problem_key"],
                        "title": row["title"],
                        "reason": (
                            "high_probability"
                            if row["probability"] >= 0.40
                            else "material_probability_increase"
                        ),
                        "probability": row["probability"],
                        "probability_change": row[
                            "probability_change"
                        ],
                        "confidence": row["confidence"],
                        "raw_confidence": row.get(
                            "raw_confidence"
                        ),
                        "confidence_status": row.get(
                            "confidence_status"
                        ),
                    }
                )

        return {
            "status": "success",
            "generated_at": self._utcnow().isoformat(),
            "system_bluf": system_bluf,
            "system_posture": {
                "active_warning_problems": len(
                    warning_rows
                ),
                "highest_risk_warning": highest,
                "largest_probability_change": (
                    largest_change
                ),
                "material_change_count": len(
                    material_changes
                ),
                "recent_propagation_count": len(
                    propagation_rows
                ),
                "latest_pipeline_run": pipeline,
            },
            "top_warnings": warning_rows[:warning_limit],
            "material_changes": material_changes,
            "recent_propagations": propagation_rows,
            "regional_posture": regional_posture,
            "latest_products": product_rows,
            "immediate_watch_items": watch_items[:12],
            "metadata": {
                "propagation_window_hours": (
                    propagation_hours
                ),
                "warning_limit": warning_limit,
                "product_limit": product_limit,
                "source_of_truth": {
                    "warnings": "sews_warning_problems",
                    "assessments": "sews_causal_assessments",
                    "products": "sews_intelligence_products",
                    "propagations": (
                        "sews_cross_warning_propagation_runs"
                    ),
                    "pipeline": "sews_pipeline_runs",
                },
            },
        }
