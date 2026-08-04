from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from supabase import Client

from app.schemas.sews_evidence import IndicatorStateRecalculateRequest
from app.services.sews_causal_propagation_service import (
    SEWSCausalPropagationService,
)
from app.services.sews_indicator_state_service import (
    SEWSIndicatorStateService,
)
from app.services.sews_strategic_intelligence_production_service import (
    SEWSStrategicIntelligenceProductionService,
)


PIPELINE_VERSION = "sews-incremental-evidence-pipeline-v1.0.0"


@dataclass(slots=True)
class IncrementalPipelineConfig:
    checkpoint_path: str = ".sews/incremental_evidence_checkpoint.json"
    lookback_days: int = 30
    stale_after_hours: int = 72
    minimum_evidence: int = 2
    persist_causal_assessments: bool = True
    reset_checkpoint: bool = False


class SEWSIncrementalEvidencePipeline:
    """
    Incrementally update only warning problems and indicators affected by
    newly collected SEWS raw evidence.

    Processing flow:
      1. Read new sews_raw_evidence since the last checkpoint.
      2. Extract warning_problem_key from evidence metadata.
      3. Load only indicator mappings for affected warning problems.
      4. Recalculate only those indicator-state contexts.
      5. Re-run causal propagation only for affected warning problems.
      6. Save a durable checkpoint after successful processing.

    The pipeline does not fabricate observations or confidence. It relies on
    the existing evidence/observation layer and state service.
    """

    def __init__(self, db: Client):
        self.db = db

    @staticmethod
    def _read_checkpoint(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}

    @staticmethod
    def _write_checkpoint(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str)
        )
        temporary.replace(path)

    def _new_evidence(
        self,
        *,
        since: str | None,
    ) -> list[dict[str, Any]]:
        query = (
            self.db.table("sews_raw_evidence")
            .select("id,collected_at,metadata,status")
            .order("collected_at")
            .range(0, 99999)
        )

        if since:
            query = query.gt("collected_at", since)

        return query.execute().data or []

    @staticmethod
    def _problem_keys(
        evidence_rows: list[dict[str, Any]],
    ) -> list[str]:
        keys: set[str] = set()

        for row in evidence_rows:
            metadata = row.get("metadata") or {}
            key = metadata.get("warning_problem_key")
            if key:
                keys.add(str(key))

            for value in metadata.get("warning_problem_keys") or []:
                if value:
                    keys.add(str(value))

        return sorted(keys)

    def _mappings(
        self,
        problem_keys: list[str],
    ) -> list[dict[str, Any]]:
        if not problem_keys:
            return []

        return (
            self.db.table("sews_warning_problem_indicators")
            .select("problem_key,indicator_key,active")
            .in_("problem_key", problem_keys)
            .eq("active", True)
            .range(0, 99999)
            .execute()
            .data
            or []
        )

    def _latest_product(
        self,
        problem_key: str,
    ) -> dict[str, Any] | None:
        result = (
            self.db.table("sews_intelligence_products")
            .select(
                "id,warning_problem_key,causal_assessment_id,"
                "probability,confidence,trend,generated_at"
            )
            .eq("warning_problem_key", problem_key)
            .order("generated_at", desc=True)
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None

    @staticmethod
    def _direction(
        current_probability: float,
        previous_probability: float | None,
    ) -> str:
        if previous_probability is None:
            return "STABLE"

        change = current_probability - previous_probability

        if change >= 0.03:
            return "DETERIORATING"

        if change <= -0.03:
            return "IMPROVING"

        return "STABLE"

    def _material_change(
        self,
        *,
        problem_key: str,
        probability: float,
        confidence: float,
    ) -> tuple[bool, list[str]]:
        previous = self._latest_product(problem_key)

        if not previous:
            return True, ["no_previous_product"]

        previous_probability = float(
            previous.get("probability") or 0
        )
        previous_confidence = float(
            previous.get("confidence") or 0
        )
        previous_trend = str(
            previous.get("trend") or "STABLE"
        ).upper()

        current_trend = self._direction(
            probability,
            previous_probability,
        )

        reasons: list[str] = []

        if abs(probability - previous_probability) >= 0.02:
            reasons.append("probability_changed")

        if abs(confidence - previous_confidence) >= 5.0:
            reasons.append("confidence_changed")

        if current_trend != previous_trend:
            reasons.append("direction_changed")

        return bool(reasons), reasons

    def run(
        self,
        config: IncrementalPipelineConfig | None = None,
    ) -> dict[str, Any]:
        config = config or IncrementalPipelineConfig()
        checkpoint_path = Path(config.checkpoint_path)

        if config.reset_checkpoint and checkpoint_path.exists():
            checkpoint_path.unlink()

        checkpoint = self._read_checkpoint(checkpoint_path)
        since = checkpoint.get("last_collected_at")

        evidence_rows = self._new_evidence(since=since)
        problem_keys = self._problem_keys(evidence_rows)

        if not evidence_rows:
            return {
                "pipeline_version": PIPELINE_VERSION,
                "status": "no_changes",
                "new_evidence_records": 0,
                "affected_warning_problems": 0,
                "indicator_contexts_recalculated": 0,
                "causal_assessments_updated": 0,
                "checkpoint_path": str(checkpoint_path),
            }

        latest_collected_at = max(
            str(row["collected_at"])
            for row in evidence_rows
            if row.get("collected_at")
        )

        if not problem_keys:
            self._write_checkpoint(
                checkpoint_path,
                {
                    "pipeline_version": PIPELINE_VERSION,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "last_collected_at": latest_collected_at,
                    "last_evidence_id": evidence_rows[-1].get("id"),
                    "note": (
                        "Evidence was found, but no warning_problem_key "
                        "was present in metadata."
                    ),
                },
            )
            return {
                "pipeline_version": PIPELINE_VERSION,
                "status": "no_routable_evidence",
                "new_evidence_records": len(evidence_rows),
                "affected_warning_problems": 0,
                "indicator_contexts_recalculated": 0,
                "causal_assessments_updated": 0,
                "checkpoint_path": str(checkpoint_path),
            }

        mappings = self._mappings(problem_keys)
        contexts = sorted({
            (str(row["problem_key"]), str(row["indicator_key"]))
            for row in mappings
            if row.get("problem_key") and row.get("indicator_key")
        })

        state_service = SEWSIndicatorStateService(self.db)
        causal_service = SEWSCausalPropagationService(self.db)

        state_results: list[dict[str, Any]] = []
        state_errors: list[dict[str, str]] = []

        for problem_key, indicator_key in contexts:
            try:
                state = state_service.recalculate(
                    IndicatorStateRecalculateRequest(
                        indicator_key=indicator_key,
                        warning_problem_key=problem_key,
                        lookback_days=config.lookback_days,
                        stale_after_hours=config.stale_after_hours,
                        minimum_evidence=config.minimum_evidence,
                    )
                )

                state_results.append({
                    "problem_key": problem_key,
                    "indicator_key": indicator_key,
                    "status": str(
                        getattr(state.status, "value", state.status)
                    ),
                    "current_value": state.current_value,
                    "confidence": state.confidence,
                })

            except Exception as exc:
                state_errors.append({
                    "problem_key": problem_key,
                    "indicator_key": indicator_key,
                    "error": f"{type(exc).__name__}: {exc}",
                })

        causal_results: list[dict[str, Any]] = []
        causal_errors: list[dict[str, str]] = []

        for problem_key in problem_keys:
            try:
                result = causal_service.propagate(
                    problem_key,
                    persist=config.persist_causal_assessments,
                )
                causal_results.append({
                    "problem_key": problem_key,
                    "outcome_probability": result.get(
                        "outcome_probability"
                    ),
                    "confidence_score": result.get("confidence_score"),
                    "causal_assessment_id": result.get(
                        "causal_assessment_id"
                    ),
                })
            except Exception as exc:
                causal_errors.append({
                    "problem_key": problem_key,
                    "error": f"{type(exc).__name__}: {exc}",
                })

        product_service = (
            SEWSStrategicIntelligenceProductionService(
                self.db
            )
        )

        product_results: list[dict[str, Any]] = []
        product_errors: list[dict[str, str]] = []
        products_skipped: list[dict[str, Any]] = []

        for causal_result in causal_results:
            problem_key = causal_result["problem_key"]
            probability = float(
                causal_result.get("outcome_probability") or 0
            )
            confidence = float(
                causal_result.get("confidence_score") or 0
            )

            try:
                material_change, reasons = (
                    self._material_change(
                        problem_key=problem_key,
                        probability=probability,
                        confidence=confidence,
                    )
                )

                if not material_change:
                    products_skipped.append(
                        {
                            "problem_key": problem_key,
                            "reason": "no_material_change",
                        }
                    )
                    continue

                product = product_service.generate(
                    problem_key,
                    persist=True,
                )

                product_results.append(
                    {
                        "problem_key": problem_key,
                        "product_id": product.get("id"),
                        "probability": product.get(
                            "probability"
                        ),
                        "confidence": product.get(
                            "confidence"
                        ),
                        "trend": product.get("trend"),
                        "material_change_reasons": reasons,
                    }
                )

            except Exception as exc:
                product_errors.append(
                    {
                        "problem_key": problem_key,
                        "error": (
                            f"{type(exc).__name__}: {exc}"
                        ),
                    }
                )

        completed = (
            not state_errors
            and not causal_errors
            and not product_errors
        )

        if completed:
            self._write_checkpoint(
                checkpoint_path,
                {
                    "pipeline_version": PIPELINE_VERSION,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "last_collected_at": latest_collected_at,
                    "last_evidence_id": evidence_rows[-1].get("id"),
                    "affected_warning_problems": problem_keys,
                    "indicator_contexts_recalculated": len(state_results),
                    "causal_assessments_updated": len(causal_results),
                    "intelligence_products_generated": len(
                        product_results
                    ),
                    "intelligence_products_skipped": len(
                        products_skipped
                    ),
                },
            )

        return {
            "pipeline_version": PIPELINE_VERSION,
            "status": "success" if completed else "partial",
            "new_evidence_records": len(evidence_rows),
            "affected_warning_problem_keys": problem_keys,
            "affected_warning_problems": len(problem_keys),
            "indicator_contexts_considered": len(contexts),
            "indicator_contexts_recalculated": len(state_results),
            "indicator_state_errors": state_errors,
            "causal_assessments_updated": len(causal_results),
            "causal_results": causal_results,
            "causal_errors": causal_errors,
            "intelligence_products_generated": len(
                product_results
            ),
            "intelligence_product_results": product_results,
            "intelligence_products_skipped": len(
                products_skipped
            ),
            "intelligence_product_skips": products_skipped,
            "intelligence_product_errors": product_errors,
            "checkpoint_advanced": completed,
            "checkpoint_path": str(checkpoint_path),
        }
