from __future__ import annotations

from typing import Any

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)

from app.services.conflict_intelligence.observation_ingestion_service import (
    ConflictObservationIngestionService,
)

from app.services.conflict_intelligence.conflict_state_engine import (
    ConflictStateEngine,
)


class ConflictEvidenceObservationBridge:

    def __init__(self) -> None:
        self.db = get_supabase_client()
        self.ingestion = ConflictObservationIngestionService()

    def _evidence_rows(
        self,
        *,
        conflict_id: int | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:

        query = (
            self.db.table("conflict_evidence")
            .select("*")
            .eq("active", True)
            .in_(
                "review_status",
                [
                    "validated",
                    "provisional",
                ],
            )
            .order("observed_at", desc=True)
            .limit(limit)
        )

        if conflict_id is not None:
            query = query.eq(
                "conflict_id",
                conflict_id,
            )

        return (
            query.execute().data
            or []
        )

    @staticmethod
    def _observation_payload(
        evidence: dict[str, Any],
    ) -> dict[str, Any]:

        countries = (
            evidence.get("countries")
            or []
        )

        primary_country = (
            str(countries[0]).upper()
            if countries
            else None
        )

        severity = evidence.get(
            "severity"
        )

        if severity is not None:
            severity = int(
                round(
                    float(severity)
                )
            )

        return {
            "observed_at":
                evidence.get("observed_at")
                or evidence.get("published_at"),

            "source":
                evidence.get("source_name")
                or evidence.get("source")
                or "unknown",

            "source_url":
                evidence.get("source_url"),

            "source_version":
                "conflict-evidence-v1",

            "title":
                evidence.get("title"),

            "summary":
                evidence.get("summary"),

            "country_iso3":
                primary_country,

            "related_state_iso3":
                [
                    str(x).upper()
                    for x in countries
                    if x
                ],

            "conflict_id":
                evidence.get("conflict_id"),

            "event_type":
                evidence.get("event_type")
                or "other",

            "severity":
                severity,

            "confidence":
                evidence.get("confidence"),

            "observation_data": {
                "evidence_id":
                    evidence.get("id"),

                "evidence_key":
                    evidence.get("evidence_key"),

                "citation_text":
                    evidence.get("citation_text"),

                "supports_escalation":
                    evidence.get("supports_escalation"),

                "contradicts_escalation":
                    evidence.get("contradicts_escalation"),

                "source_reliability":
                    evidence.get("source_reliability"),

                "review_status":
                    evidence.get("review_status"),

                "evidence_type":
                    evidence.get("evidence_type"),
            },
        }

    def _recompute_state(
        self,
        conflict_id: int,
    ) -> dict[str, Any]:

        engine = ConflictStateEngine()

        for method_name in (
            "assess",
            "calculate",
            "run",
        ):
            method = getattr(
                engine,
                method_name,
                None,
            )

            if method is None:
                continue

            try:
                return method(
                    conflict_id
                )
            except TypeError:
                continue

        return {
            "available": False,
            "reason":
                "No compatible state-engine method found.",
        }

    def run(
        self,
        *,
        conflict_id: int | None = None,
        limit: int = 500,
        recompute_state: bool = True,
    ) -> dict[str, Any]:

        rows = self._evidence_rows(
            conflict_id=conflict_id,
            limit=limit,
        )

        created = 0
        existing = 0
        skipped = 0
        errors = []
        affected_conflicts: set[int] = set()

        for evidence in rows:

            try:
                if not evidence.get("conflict_id"):
                    skipped += 1
                    continue

                if not (
                    evidence.get("observed_at")
                    or evidence.get("published_at")
                ):
                    skipped += 1
                    continue

                payload = self._observation_payload(
                    evidence
                )

                result = self.ingestion.ingest(
                    payload
                )

                cid = result.get(
                    "conflict_id"
                )

                if cid is not None:
                    affected_conflicts.add(
                        int(cid)
                    )

                if result.get("created"):
                    created += 1
                else:
                    existing += 1

            except Exception as exc:
                errors.append(
                    {
                        "evidence_key":
                            evidence.get(
                                "evidence_key"
                            ),

                        "error":
                            (
                                f"{type(exc).__name__}: "
                                f"{exc}"
                            ),
                    }
                )

        state_results = {}

        if recompute_state:
            for cid in sorted(
                affected_conflicts
            ):
                try:
                    state_results[
                        str(cid)
                    ] = self._recompute_state(
                        cid
                    )
                except Exception as exc:
                    state_results[
                        str(cid)
                    ] = {
                        "available":
                            False,

                        "error":
                            (
                                f"{type(exc).__name__}: "
                                f"{exc}"
                            ),
                    }

        return {
            "status":
                "success",

            "evidence_checked":
                len(rows),

            "observations_created":
                created,

            "observations_existing":
                existing,

            "skipped":
                skipped,

            "affected_conflicts":
                sorted(
                    affected_conflicts
                ),

            "state_recomputed":
                recompute_state,

            "state_results":
                state_results,

            "error_count":
                len(errors),

            "errors":
                errors[:20],
        }
