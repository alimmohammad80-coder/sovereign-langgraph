from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from supabase import Client


PIPELINE_VERSION = "sews-production-pipeline-v1.0.0"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class SEWSPipelineError(RuntimeError):
    pass


@dataclass(frozen=True)
class PipelineStage:
    key: str
    command: list[str]
    required: bool = True


class SEWSPipelineOrchestrator:
    """
    One auditable production entry point for the existing SEWS services.

    This deliberately reuses the established scripts instead of duplicating
    collection, scoring, propagation, or product-generation logic.
    """

    def __init__(self, db: Client, *, project_root: Path | None = None):
        self.db = db
        self.project_root = project_root or PROJECT_ROOT

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _extract_summary(stdout: str) -> dict[str, Any]:
        """
        Parse the final balanced Python dictionary printed by existing runners.

        The runners use pprint, so summaries often span many lines and cannot
        be parsed one line at a time.
        """
        candidates: list[str] = []
        start: int | None = None
        depth = 0
        quote: str | None = None
        escaped = False

        for index, char in enumerate(stdout):
            if quote is not None:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
                continue

            if char in {"'", '"'}:
                quote = char
                continue

            if char == "{":
                if depth == 0:
                    start = index
                depth += 1
                continue

            if char == "}" and depth > 0:
                depth -= 1

                if depth == 0 and start is not None:
                    candidates.append(
                        stdout[start:index + 1]
                    )
                    start = None

        for candidate in reversed(candidates):
            try:
                parsed = ast.literal_eval(candidate)
            except (SyntaxError, ValueError):
                continue

            if isinstance(parsed, dict):
                return parsed

        return {}

    def _insert_run(
        self,
        *,
        run_key: str,
        mode: str,
        source_keys: list[str],
        metadata: dict[str, Any],
    ) -> str:
        row = {
            "run_key": run_key,
            "mode": mode,
            "status": "RUNNING",
            "source_keys": source_keys,
            "stages": [],
            "errors": [],
            "pipeline_version": PIPELINE_VERSION,
            "metadata": metadata,
        }
        result = self.db.table("sews_pipeline_runs").insert(row).execute()
        if not result.data:
            raise SEWSPipelineError("Failed to create sews_pipeline_runs record.")
        return str(result.data[0]["id"])

    def _update_run(self, run_id: str, payload: dict[str, Any]) -> None:
        self.db.table("sews_pipeline_runs").update(payload).eq("id", run_id).execute()

    def _run_stage(self, stage: PipelineStage) -> dict[str, Any]:
        started = self._utcnow()
        env = os.environ.copy()
        current_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            str(self.project_root)
            if not current_pythonpath
            else f"{self.project_root}{os.pathsep}{current_pythonpath}"
        )

        completed = subprocess.run(
            stage.command,
            cwd=self.project_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        finished = self._utcnow()
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""

        return {
            "stage_key": stage.key,
            "required": stage.required,
            "status": "SUCCESS" if completed.returncode == 0 else "FAILED",
            "return_code": completed.returncode,
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "duration_seconds": round((finished - started).total_seconds(), 3),
            "summary": self._extract_summary(stdout),
            "stdout_tail": stdout[-12000:],
            "stderr_tail": stderr[-12000:],
            "command": stage.command,
        }

    @staticmethod
    def _metric(stage_results: list[dict[str, Any]], *paths: tuple[str, ...]) -> int:
        for stage in reversed(stage_results):
            summary = stage.get("summary") or {}
            for path in paths:
                value: Any = summary
                for key in path:
                    if not isinstance(value, dict):
                        value = None
                        break
                    value = value.get(key)
                if isinstance(value, (int, float)):
                    return int(value)
        return 0

    def run_once(
        self,
        *,
        source_keys: Iterable[str] = ("GOOGLE_NEWS_RSS", "GDELT"),
        batch_size: int = 2,
        limit_per_query: int = 3,
        reset_collection_checkpoint: bool = True,
        generate_products: bool = True,
        mode: str = "ONCE",
    ) -> dict[str, Any]:
        source_keys = [str(x) for x in source_keys]
        run_key = f"SEWS-{self._utcnow().strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}"
        started = self._utcnow()

        metadata = {
            "batch_size": batch_size,
            "limit_per_query": limit_per_query,
            "reset_collection_checkpoint": reset_collection_checkpoint,
            "generate_products": generate_products,
        }
        run_id = self._insert_run(
            run_key=run_key,
            mode=mode,
            source_keys=source_keys,
            metadata=metadata,
        )

        collection_command = [
            sys.executable,
            "scripts/run_scheduled_sews_workflow.py",
            "--mode",
            "once",
            "--sources",
            *source_keys,
            "--batch-size",
            str(batch_size),
            "--limit-per-query",
            str(limit_per_query),
        ]
        if reset_collection_checkpoint:
            collection_command.append("--reset-collection-checkpoint")

        core_stages = [
            PipelineStage(
                "collection_and_incremental_processing",
                collection_command,
            ),
            PipelineStage(
                "cross_warning_propagation",
                [
                    sys.executable,
                    "scripts/run_sews_cross_warning_propagation.py",
                ],
            ),
        ]

        stage_results: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        product_problem_keys: set[str] = set()

        try:
            for stage in core_stages:
                result = self._run_stage(stage)
                stage_results.append(result)

                summary = result.get("summary") or {}

                if stage.key == (
                    "collection_and_incremental_processing"
                ):
                    incremental = (
                        summary.get("incremental_processing")
                        or {}
                    )

                    affected_problem_keys = sorted({
                        str(key)
                        for key in (
                            incremental.get(
                                "affected_warning_problem_keys"
                            )
                            or []
                        )
                        if key
                    })

                    if affected_problem_keys:
                        supervisor_stage = PipelineStage(
                            "warning_supervisors",
                            [
                                sys.executable,
                                "scripts/"
                                "run_selected_sews_warning_supervisors.py",
                                "--problem-keys",
                                *affected_problem_keys,
                                "--limit-per-query",
                                str(limit_per_query),
                            ],
                            required=False,
                        )

                        supervisor_result = self._run_stage(
                            supervisor_stage
                        )

                        stage_results.append(
                            supervisor_result
                        )

                        supervisor_summary = (
                            supervisor_result.get(
                                "summary"
                            )
                            or {}
                        )

                        product_problem_keys.update(
                            str(key)
                            for key in (
                                supervisor_summary.get(
                                    "material_changed_problem_keys"
                                )
                                or []
                            )
                            if key
                        )

                        if (
                            supervisor_result["status"]
                            == "FAILED"
                        ):
                            errors.append(
                                {
                                    "stage_key": (
                                        "warning_supervisors"
                                    ),
                                    "return_code": (
                                        supervisor_result[
                                            "return_code"
                                        ]
                                    ),
                                    "stderr_tail": (
                                        supervisor_result[
                                            "stderr_tail"
                                        ]
                                    ),
                                }
                            )

                elif stage.key == "cross_warning_propagation":
                    for update in summary.get("updates") or []:
                        source_key = update.get(
                            "source_problem_key"
                        )
                        target_key = update.get(
                            "target_problem_key"
                        )

                        if source_key:
                            product_problem_keys.add(
                                str(source_key)
                            )

                        if target_key:
                            product_problem_keys.add(
                                str(target_key)
                            )

                self._update_run(
                    run_id,
                    {
                        "stages": stage_results,
                        "metadata": {
                            **metadata,
                            "incremental_product_problem_keys": (
                                sorted(product_problem_keys)
                            ),
                        },
                    },
                )

                if result["status"] == "FAILED":
                    error = {
                        "stage_key": stage.key,
                        "return_code": result["return_code"],
                        "stderr_tail": result["stderr_tail"],
                    }
                    errors.append(error)

                    if stage.required:
                        raise SEWSPipelineError(
                            "Required pipeline stage failed: "
                            f"{stage.key}"
                        )

            if generate_products and product_problem_keys:
                product_stage = PipelineStage(
                    "strategic_intelligence_products",
                    [
                        sys.executable,
                        "scripts/"
                        "generate_all_sews_intelligence_products.py",
                        "--problem-keys",
                        *sorted(product_problem_keys),
                    ],
                )

                product_result = self._run_stage(
                    product_stage
                )
                stage_results.append(product_result)

                self._update_run(
                    run_id,
                    {
                        "stages": stage_results,
                        "metadata": {
                            **metadata,
                            "incremental_product_problem_keys": (
                                sorted(product_problem_keys)
                            ),
                            "incremental_product_count": len(
                                product_problem_keys
                            ),
                        },
                    },
                )

                if product_result["status"] == "FAILED":
                    errors.append(
                        {
                            "stage_key": product_stage.key,
                            "return_code": product_result[
                                "return_code"
                            ],
                            "stderr_tail": product_result[
                                "stderr_tail"
                            ],
                        }
                    )

                    if product_stage.required:
                        raise SEWSPipelineError(
                            "Required pipeline stage failed: "
                            f"{product_stage.key}"
                        )

            elif generate_products:
                stage_results.append(
                    {
                        "stage_key": (
                            "strategic_intelligence_products"
                        ),
                        "required": False,
                        "status": "SKIPPED",
                        "return_code": 0,
                        "started_at": self._utcnow().isoformat(),
                        "finished_at": self._utcnow().isoformat(),
                        "duration_seconds": 0.0,
                        "summary": {
                            "incremental_mode": True,
                            "warning_problems_processed": 0,
                            "products_generated": 0,
                            "reason": (
                                "no_affected_or_propagated_warnings"
                            ),
                        },
                        "stdout_tail": "",
                        "stderr_tail": "",
                        "command": [],
                    }
                )

                self._update_run(
                    run_id,
                    {
                        "stages": stage_results,
                        "metadata": {
                            **metadata,
                            "incremental_product_problem_keys": [],
                            "incremental_product_count": 0,
                        },
                    },
                )

            status = "SUCCESS"
        except Exception as exc:
            status = "FAILED"
            if not errors:
                errors.append(
                    {
                        "stage_key": "orchestrator",
                        "error_type": type(exc).__name__,
                        "message": str(exc),
                    }
                )

        finished = self._utcnow()

        warnings_updated = self._metric(
            stage_results,
            ("incremental_processing", "affected_warning_problems"),
            ("affected_warning_problems",),
            ("warning_problems_processed",),
        )
        indicators_updated = self._metric(
            stage_results,
            ("incremental_processing", "indicator_contexts_recalculated"),
            ("indicator_contexts_recalculated",),
        )
        evidence_records = self._metric(
            stage_results,
            ("collection", "records_persisted"),
            ("records_persisted",),
            ("incremental_processing", "new_evidence_records"),
        )
        propagation_events = self._metric(
            stage_results,
            ("propagations_created",),
        )
        products_generated = self._metric(
            stage_results,
            (
                "incremental_processing",
                "intelligence_products_generated",
            ),
            ("products_generated",),
        )

        final_payload = {
            "status": status,
            "finished_at": finished.isoformat(),
            "duration_seconds": round((finished - started).total_seconds(), 3),
            "stages": stage_results,
            "warnings_updated": warnings_updated,
            "indicators_updated": indicators_updated,
            "evidence_records": evidence_records,
            "propagation_events": propagation_events,
            "products_generated": products_generated,
            "errors": errors,
        }
        self._update_run(run_id, final_payload)

        return {
            "run_id": run_id,
            "run_key": run_key,
            "pipeline_version": PIPELINE_VERSION,
            **final_payload,
        }

    def run_forever(
        self,
        *,
        interval_minutes: int = 60,
        **kwargs: Any,
    ) -> None:
        if interval_minutes < 1:
            raise ValueError("interval_minutes must be at least 1.")

        cycle = 0
        while True:
            cycle += 1
            result = self.run_once(mode="FOREVER", **kwargs)
            print(
                f"✅ Production cycle {cycle} completed "
                f"with status={result['status']} run_id={result['run_id']}"
            )
            sleep_seconds = interval_minutes * 60
            print(f"Next cycle in {sleep_seconds} seconds.")
            time.sleep(sleep_seconds)
