from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)


class SupplyChainAnalysisJobService:
    """Persistent lifecycle for resumable supply-chain report generation."""

    def __init__(self) -> None:
        self.db = get_supabase_client()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def create(
        self,
        *,
        entity_type: str,
        entity_name: str,
        request_json: dict[str, Any],
    ) -> dict[str, Any]:
        row = {
            "entity_type": entity_type,
            "entity_name": entity_name,
            "request_json": request_json,
            "status": "queued",
        }
        result = (
            self.db.table("supply_chain_analysis_jobs")
            .insert(row)
            .execute()
        )
        if not result.data:
            raise RuntimeError("Failed to create supply-chain analysis job.")
        return result.data[0]

    def get(self, job_id: str) -> dict[str, Any] | None:
        rows = (
            self.db.table("supply_chain_analysis_jobs")
            .select("*")
            .eq("id", job_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        return rows[0] if rows else None

    def _update(self, job_id: str, values: dict[str, Any]) -> None:
        values["updated_at"] = self._now()
        (
            self.db.table("supply_chain_analysis_jobs")
            .update(values)
            .eq("id", job_id)
            .execute()
        )

    def mark_processing(self, job_id: str) -> None:
        self._update(
            job_id,
            {
                "status": "processing",
                "started_at": self._now(),
                "error_message": None,
            },
        )

    def complete(self, job_id: str, result: dict[str, Any]) -> None:
        report = result.get("report") if isinstance(result, dict) else None
        report = report if isinstance(report, dict) else {}
        qa = {
            "passed": report.get("generation_status") == "validated",
            "analysis_word_count": report.get("analysis_word_count"),
            "citation_style": report.get("citation_style"),
            "citation_count": report.get("citation_count"),
            "entity_type": report.get("entity_type"),
            "entity_name": report.get("entity_name"),
        }
        self._update(
            job_id,
            {
                "status": "completed",
                "provider": report.get("provider"),
                "model": report.get("model"),
                "result": result,
                "qa": qa,
                "completed_at": self._now(),
            },
        )

    def fail(self, job_id: str, exc: Exception) -> None:
        self._update(
            job_id,
            {
                "status": "failed",
                "error_message": f"{type(exc).__name__}: {exc}",
                "completed_at": self._now(),
            },
        )
