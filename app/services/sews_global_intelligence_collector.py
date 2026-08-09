from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from supabase import Client

from app.sews_bridge.orchestrator import SEWSExistingSourcesBridge
from app.sews_bridge.schemas import BridgeRunRequest


COLLECTOR_VERSION = "sews-global-intelligence-collector-v1.0.0"
DEFAULT_SOURCE_KEYS = ("GOOGLE_NEWS_RSS", "GDELT", "NEWSAPI")


@dataclass(slots=True)
class GlobalCollectionConfig:
    source_keys: tuple[str, ...] = DEFAULT_SOURCE_KEYS
    limit_per_query: int = 5
    problem_batch_size: int = 4
    persist: bool = True
    dry_run: bool = False
    continue_on_error: bool = True
    checkpoint_path: str = ".sews/global_collection_checkpoint.json"


class SEWSGlobalIntelligenceCollector:
    """Resumable global collection over all active SEWS warning problems."""

    def __init__(self, db: Client):
        self.db = db

    @staticmethod
    def _chunks(values: list[str], size: int) -> Iterable[list[str]]:
        size = max(1, int(size))
        for index in range(0, len(values), size):
            yield values[index:index + size]

    def _latest_successful_cycle(self) -> str | None:
        rows = (
            self.db.table("sews_pipeline_runs")
            .select("finished_at")
            .eq("status", "SUCCESS")
            .not_.is_("finished_at", "null")
            .order("finished_at", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )

        if not rows:
            return None

        return rows[0].get("finished_at")

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

    async def collect_all(
        self,
        config: GlobalCollectionConfig | None = None,
        *,
        resume: bool = True,
        reset_checkpoint: bool = False,
    ) -> dict[str, Any]:
        config = config or GlobalCollectionConfig()
        checkpoint_path = Path(config.checkpoint_path)

        if reset_checkpoint and checkpoint_path.exists():
            checkpoint_path.unlink()

        problem_keys = self._active_problem_keys()
        if not problem_keys:
            raise RuntimeError("No active SEWS warning problems were found.")

        checkpoint = self._read_checkpoint(checkpoint_path) if resume else {}
        completed = set(checkpoint.get("completed_problem_keys") or [])
        remaining = [key for key in problem_keys if key not in completed]

        started_at = datetime.now(timezone.utc)
        collect_since = self._latest_successful_cycle()

        print(
            "Freshness cutoff:",
            collect_since or "FIRST_RUN",
        )

        records_received = 0
        records_persisted = 0
        batches_completed = 0
        source_results: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        bridge = SEWSExistingSourcesBridge(self.db)
        total_batches = (
            len(remaining) + config.problem_batch_size - 1
        ) // config.problem_batch_size

        for batch_number, batch in enumerate(
            self._chunks(remaining, config.problem_batch_size),
            start=1,
        ):
            print(
                f"[Batch {batch_number}/{total_batches}] "
                + ", ".join(batch)
            )

            try:
                result = await bridge.run(
                    BridgeRunRequest(
                        problem_keys=batch,
                        source_keys=list(config.source_keys),
                        limit_per_query=config.limit_per_query,
                        collect_since=collect_since,
                        persist=config.persist and not config.dry_run,
                        dry_run=config.dry_run,
                    )
                )
                payload = result.model_dump(mode="json")
                batch_received = int(payload.get("total_records_received") or 0)
                batch_persisted = int(payload.get("total_records_persisted") or 0)
                records_received += batch_received
                records_persisted += batch_persisted
                source_results.extend(payload.get("source_results") or [])
                completed.update(batch)
                batches_completed += 1
                print(f"  ✅ received={batch_received} persisted={batch_persisted}")
            except Exception as exc:
                error = {
                    "batch_number": batch_number,
                    "problem_keys": batch,
                    "error": f"{type(exc).__name__}: {exc}",
                }
                errors.append(error)
                print(f"  ❌ {error['error']}")
                if not config.continue_on_error:
                    raise

            self._write_checkpoint(
                checkpoint_path,
                {
                    "collector_version": COLLECTOR_VERSION,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "completed_problem_keys": sorted(completed),
                    "last_batch_number": batch_number,
                    "records_received": records_received,
                    "records_persisted": records_persisted,
                    "errors": errors,
                },
            )
            await asyncio.sleep(0)

        finished_at = datetime.now(timezone.utc)
        return {
            "collector_version": COLLECTOR_VERSION,
            "status": "success" if not errors else "partial",
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "collect_since": collect_since,
            "active_warning_problems": len(problem_keys),
            "already_completed_on_resume": len(set(problem_keys) - set(remaining)),
            "warning_problems_attempted": len(remaining),
            "warning_problems_completed_total": len(completed),
            "batches_completed": batches_completed,
            "records_received": records_received,
            "records_persisted": records_persisted,
            "source_results": source_results,
            "errors": errors,
            "checkpoint_path": str(checkpoint_path),
        }
