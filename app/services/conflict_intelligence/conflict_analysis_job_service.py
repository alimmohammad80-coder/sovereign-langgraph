from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)

from app.services.conflict_intelligence.conflict_intelligence_analyst import (
    ConflictIntelligenceAnalyst,
)

from app.services.conflict_intelligence.conflict_intelligence_agent import (
    ConflictIntelligenceAgent,
)

from app.services.conflict_intelligence.conflict_agent_analyst import (
    ConflictAgentAnalyst,
)


class ConflictAnalysisJobService:

    def __init__(self) -> None:
        self.db = get_supabase_client()

    @staticmethod
    def _now() -> str:
        return datetime.now(
            timezone.utc
        ).isoformat()

    def create(
        self,
        *,
        conflict_id: int | None = None,
        horizon_days: int = 365,
        lookback_days: int = 90,
        ripple_depth: int = 3,
        preferred_provider: str | None = None,
        preferred_model: str | None = None,
        request_mode: str = "canonical",
        request_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        row = {
            "conflict_id":
                conflict_id,

            "horizon_days":
                horizon_days,

            "lookback_days":
                lookback_days,

            "ripple_depth":
                ripple_depth,

            "preferred_provider":
                preferred_provider,

            "preferred_model":
                preferred_model,

            "request_mode":
                request_mode,

            "request_json":
                request_json,

            "status":
                "queued",
        }

        result = (
            self.db.table(
                "conflict_analysis_jobs"
            )
            .insert(row)
            .execute()
        )

        if not result.data:
            raise RuntimeError(
                "Failed to create conflict analysis job."
            )

        return result.data[0]

    def get(
        self,
        job_id: str,
    ) -> dict[str, Any] | None:

        rows = (
            self.db.table(
                "conflict_analysis_jobs"
            )
            .select("*")
            .eq("id", job_id)
            .limit(1)
            .execute()
            .data
            or []
        )

        return (
            rows[0]
            if rows
            else None
        )

    def _update(
        self,
        job_id: str,
        values: dict[str, Any],
    ) -> None:

        values[
            "updated_at"
        ] = self._now()

        (
            self.db.table(
                "conflict_analysis_jobs"
            )
            .update(values)
            .eq("id", job_id)
            .execute()
        )

    def _run_canonical(
        self,
        job: dict[str, Any],
    ) -> dict[str, Any]:

        conflict_id = (
            job.get(
                "conflict_id"
            )
        )

        if conflict_id is None:
            raise ValueError(
                "Canonical analysis job "
                "requires conflict_id."
            )

        return (
            ConflictIntelligenceAnalyst()
            .analyze(
                conflict_id=
                    int(conflict_id),

                horizon_days=
                    int(
                        job[
                            "horizon_days"
                        ]
                    ),

                lookback_days=
                    int(
                        job[
                            "lookback_days"
                        ]
                    ),

                ripple_depth=
                    int(
                        job[
                            "ripple_depth"
                        ]
                    ),

                preferred_provider=
                    job.get(
                        "preferred_provider"
                    ),

                preferred_model=
                    job.get(
                        "preferred_model"
                    ),
            )
        )

    def _run_agent_selection(
        self,
        job: dict[str, Any],
    ) -> dict[str, Any]:

        request = (
            job.get(
                "request_json"
            )
            or {}
        )

        packet = (
            ConflictIntelligenceAgent()
            .build_packet(
                countries=
                    request.get(
                        "countries"
                    )
                    or [],

                region=
                    request.get(
                        "region"
                    ),

                conflict_type=
                    request.get(
                        "conflict_type"
                    ),

                indicators=
                    request.get(
                        "indicators"
                    )
                    or [],

                horizon_days=
                    int(
                        request.get(
                            "horizon_days",
                            365,
                        )
                    ),

                lookback_days=
                    int(
                        request.get(
                            "lookback_days",
                            90,
                        )
                    ),

                ripple_depth=
                    int(
                        request.get(
                            "ripple_depth",
                            3,
                        )
                    ),
            )
        )

        return (
            ConflictAgentAnalyst()
            .analyze(
                packet,

                preferred_provider=
                    job.get(
                        "preferred_provider"
                    ),

                preferred_model=
                    job.get(
                        "preferred_model"
                    ),
            )
        )

    def run(
        self,
        job_id: str,
    ) -> None:

        job = self.get(
            job_id
        )

        if not job:
            return

        self._update(
            job_id,
            {
                "status":
                    "processing",

                "started_at":
                    self._now(),

                "error_message":
                    None,
            },
        )

        try:

            mode = (
                job.get(
                    "request_mode"
                )
                or "canonical"
            )

            if (
                mode
                == "agent_selection"
            ):
                result = (
                    self._run_agent_selection(
                        job
                    )
                )
            else:
                result = (
                    self._run_canonical(
                        job
                    )
                )

            self._update(
                job_id,
                {
                    "status":
                        "completed",

                    "provider":
                        result.get(
                            "provider"
                        ),

                    "model":
                        result.get(
                            "model"
                        ),

                    "result":
                        result,

                    "qa":
                        result.get(
                            "qa"
                        ),

                    "completed_at":
                        self._now(),
                },
            )

        except Exception as exc:

            self._update(
                job_id,
                {
                    "status":
                        "failed",

                    "error_message":
                        (
                            f"{type(exc).__name__}: "
                            f"{exc}"
                        ),

                    "completed_at":
                        self._now(),
                },
            )
