from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)


class ConflictReportPersistence:

    def __init__(self) -> None:
        self.db = get_supabase_client()

    @staticmethod
    def _report_key(
        *,
        conflict_id: int,
        analyst_version: str,
        packet_version: str,
        model: str | None,
    ) -> str:

        raw = "|".join(
            [
                str(conflict_id),
                analyst_version,
                packet_version,
                model or "",
                datetime.now(
                    timezone.utc
                ).strftime(
                    "%Y-%m-%dT%H"
                ),
            ]
        )

        digest = hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest()[:24].upper()

        return f"CIR-{digest}"

    def persist(
        self,
        *,
        conflict_id: int,
        analyst_version: str,
        packet_version: str,
        provider: str | None,
        model: str | None,
        report: dict[str, Any],
        qa: dict[str, Any],
    ) -> dict[str, Any]:

        report_key = self._report_key(
            conflict_id=conflict_id,
            analyst_version=analyst_version,
            packet_version=packet_version,
            model=model,
        )

        now = datetime.now(
            timezone.utc
        ).isoformat()

        row = {
            "report_key":
                report_key,

            "conflict_id":
                conflict_id,

            "analyst_version":
                analyst_version,

            "packet_version":
                packet_version,

            "provider":
                provider,

            "model":
                model,

            "bluf":
                report.get("bluf"),

            "executive_judgment":
                report.get(
                    "executive_judgment"
                ),

            "current_situation":
                report.get(
                    "current_situation"
                ),

            "key_drivers":
                report.get(
                    "key_drivers"
                )
                or [],

            "contrary_evidence":
                report.get(
                    "contrary_evidence"
                )
                or [],

            "historical_context":
                report.get(
                    "historical_context"
                ),

            "escalation_pathways":
                report.get(
                    "escalation_pathways"
                )
                or [],

            "forecast_outlook":
                report.get(
                    "forecast_outlook"
                )
                or {},

            "indicators_to_watch":
                report.get(
                    "indicators_to_watch"
                )
                or [],

            "strategic_implications":
                report.get(
                    "strategic_implications"
                ),

            "confidence_assessment":
                report.get(
                    "confidence_assessment"
                ),

            "full_analysis":
                report.get(
                    "full_analysis"
                ),

            "references_json":
                report.get(
                    "references"
                )
                or [],

            "qa_passed":
                bool(
                    qa.get("passed")
                ),

            "qa_result":
                qa,

            "generated_at":
                now,

            "created_at":
                now,

            "updated_at":
                now,
        }

        result = (
            self.db.table(
                "conflict_intelligence_reports"
            )
            .upsert(
                row,
                on_conflict="report_key",
            )
            .execute()
        )

        return (
            result.data[0]
            if result.data
            else row
        )

    def latest(
        self,
        conflict_id: int,
    ) -> dict[str, Any] | None:

        rows = (
            self.db.table(
                "conflict_intelligence_reports"
            )
            .select("*")
            .eq(
                "conflict_id",
                conflict_id,
            )
            .eq(
                "qa_passed",
                True,
            )
            .order(
                "generated_at",
                desc=True,
            )
            .limit(1)
            .execute()
            .data
            or []
        )

        return rows[0] if rows else None

    def history(
        self,
        conflict_id: int,
        limit: int = 20,
    ) -> list[dict[str, Any]]:

        return (
            self.db.table(
                "conflict_intelligence_reports"
            )
            .select("*")
            .eq(
                "conflict_id",
                conflict_id,
            )
            .eq(
                "qa_passed",
                True,
            )
            .order(
                "generated_at",
                desc=True,
            )
            .limit(limit)
            .execute()
            .data
            or []
        )
