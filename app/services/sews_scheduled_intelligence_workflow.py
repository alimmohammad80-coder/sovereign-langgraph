from __future__ import annotations

import asyncio
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from supabase import Client

from app.services.sews_global_intelligence_collector import (
    GlobalCollectionConfig,
    SEWSGlobalIntelligenceCollector,
)
from app.services.sews_incremental_evidence_pipeline import (
    IncrementalPipelineConfig,
    SEWSIncrementalEvidencePipeline,
)


WORKFLOW_VERSION = "sews-scheduled-intelligence-workflow-v1.0.0"


@dataclass(slots=True)
class ScheduledWorkflowConfig:
    source_keys: tuple[str, ...] = (
        "GOOGLE_NEWS_RSS",
        "GDELT",
    )
    limit_per_query: int = 3
    problem_batch_size: int = 2
    collection_checkpoint_path: str = (
        ".sews/global_collection_checkpoint.json"
    )
    incremental_checkpoint_path: str = (
        ".sews/incremental_evidence_checkpoint.json"
    )
    workflow_state_path: str = (
        ".sews/scheduled_workflow_state.json"
    )
    lock_path: str = ".sews/scheduled_workflow.lock"
    interval_minutes: int = 60
    continue_on_collection_error: bool = True
    persist_causal_assessments: bool = True


class SEWSScheduledWorkflowError(RuntimeError):
    pass


class SEWSScheduledIntelligenceWorkflow:
    """
    Execute the operational SEWS cycle:

        global collection
        -> incremental indicator-state recalculation
        -> affected causal-assessment updates

    The workflow is:
    - checkpoint-aware,
    - safe to interrupt,
    - protected against overlapping local runs,
    - usable as a one-time command or a persistent scheduler.
    """

    def __init__(self, db: Client):
        self.db = db

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
                default=str,
            )
        )
        temporary.replace(path)

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}

    @staticmethod
    def _acquire_lock(path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            file_descriptor = os.open(
                str(path),
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
        except FileExistsError as exc:
            existing = (
                path.read_text().strip()
                if path.exists()
                else "unknown"
            )
            raise SEWSScheduledWorkflowError(
                "Another scheduled workflow run appears active. "
                f"Lock: {path}; owner: {existing}"
            ) from exc

        with os.fdopen(file_descriptor, "w") as handle:
            handle.write(
                json.dumps(
                    {
                        "pid": os.getpid(),
                        "started_at": datetime.now(
                            timezone.utc
                        ).isoformat(),
                    }
                )
            )

    @staticmethod
    def _release_lock(path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass

    @staticmethod
    def clear_stale_lock(config: ScheduledWorkflowConfig) -> None:
        Path(config.lock_path).unlink(missing_ok=True)

    async def run_once(
        self,
        config: ScheduledWorkflowConfig | None = None,
        *,
        reset_collection_checkpoint: bool = False,
        reset_incremental_checkpoint: bool = False,
    ) -> dict[str, Any]:
        config = config or ScheduledWorkflowConfig()
        lock_path = Path(config.lock_path)
        state_path = Path(config.workflow_state_path)

        self._acquire_lock(lock_path)
        started_at = datetime.now(timezone.utc)

        state = self._read_json(state_path)
        cycle_number = int(state.get("cycle_number") or 0) + 1

        try:
            collector = SEWSGlobalIntelligenceCollector(self.db)

            collection_result = await collector.collect_all(
                GlobalCollectionConfig(
                    source_keys=config.source_keys,
                    limit_per_query=max(
                        1,
                        config.limit_per_query,
                    ),
                    problem_batch_size=max(
                        1,
                        config.problem_batch_size,
                    ),
                    persist=True,
                    dry_run=False,
                    continue_on_error=(
                        config.continue_on_collection_error
                    ),
                    checkpoint_path=(
                        config.collection_checkpoint_path
                    ),
                ),
                resume=True,
                reset_checkpoint=reset_collection_checkpoint,
            )

            incremental = SEWSIncrementalEvidencePipeline(
                self.db
            )

            processing_result = incremental.run(
                IncrementalPipelineConfig(
                    checkpoint_path=(
                        config.incremental_checkpoint_path
                    ),
                    persist_causal_assessments=(
                        config.persist_causal_assessments
                    ),
                    reset_checkpoint=(
                        reset_incremental_checkpoint
                    ),
                )
            )

            finished_at = datetime.now(timezone.utc)

            result = {
                "workflow_version": WORKFLOW_VERSION,
                "status": (
                    "success"
                    if collection_result.get("status")
                    in {"success", "no_changes"}
                    and processing_result.get("status")
                    in {"success", "no_changes"}
                    else "partial"
                ),
                "cycle_number": cycle_number,
                "started_at": started_at.isoformat(),
                "finished_at": finished_at.isoformat(),
                "collection": collection_result,
                "incremental_processing": processing_result,
            }

            self._write_json(
                state_path,
                {
                    "workflow_version": WORKFLOW_VERSION,
                    "cycle_number": cycle_number,
                    "last_status": result["status"],
                    "last_started_at": result["started_at"],
                    "last_finished_at": result["finished_at"],
                    "last_collection_records_received": (
                        collection_result.get(
                            "records_received"
                        )
                    ),
                    "last_collection_records_persisted": (
                        collection_result.get(
                            "records_persisted"
                        )
                    ),
                    "last_new_evidence_records": (
                        processing_result.get(
                            "new_evidence_records"
                        )
                    ),
                    "last_affected_warning_problems": (
                        processing_result.get(
                            "affected_warning_problems"
                        )
                    ),
                    "config": asdict(config),
                },
            )

            return result

        except Exception as exc:
            finished_at = datetime.now(timezone.utc)

            self._write_json(
                state_path,
                {
                    "workflow_version": WORKFLOW_VERSION,
                    "cycle_number": cycle_number,
                    "last_status": "failed",
                    "last_started_at": started_at.isoformat(),
                    "last_finished_at": finished_at.isoformat(),
                    "last_error": (
                        f"{type(exc).__name__}: {exc}"
                    ),
                    "config": asdict(config),
                },
            )
            raise

        finally:
            self._release_lock(lock_path)

    async def run_forever(
        self,
        config: ScheduledWorkflowConfig | None = None,
    ) -> None:
        config = config or ScheduledWorkflowConfig()
        interval_seconds = max(
            60,
            int(config.interval_minutes) * 60,
        )

        while True:
            cycle_started = datetime.now(timezone.utc)

            try:
                result = await self.run_once(
                    config,
                    reset_collection_checkpoint=True,
                    reset_incremental_checkpoint=False,
                )
                print(
                    f"✅ Cycle {result['cycle_number']} "
                    f"completed with status={result['status']}"
                )
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                print(
                    "❌ Scheduled cycle failed: "
                    f"{type(exc).__name__}: {exc}"
                )

            elapsed = (
                datetime.now(timezone.utc)
                - cycle_started
            ).total_seconds()

            sleep_seconds = max(
                60,
                interval_seconds - int(elapsed),
            )

            next_run = datetime.fromtimestamp(
                datetime.now(timezone.utc).timestamp()
                + sleep_seconds,
                tz=timezone.utc,
            )

            print(
                f"Next cycle at {next_run.isoformat()} "
                f"(sleeping {sleep_seconds} seconds)."
            )

            await asyncio.sleep(sleep_seconds)
