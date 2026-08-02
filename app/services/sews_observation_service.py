from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean
from typing import Any
from uuid import uuid4

from supabase import Client

from app.schemas.sews_evidence import (
    ObservationCreateRequest,
    ObservationResponse,
)


class SEWSObservationError(RuntimeError):
    pass


class SEWSObservationService:
    def __init__(self, db: Client):
        self.db = db

    @staticmethod
    def _freshness_score(event_time: str | None) -> float:
        if not event_time:
            return 25.0
        timestamp = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        age_hours = max(
            0.0,
            (datetime.now(timezone.utc) - timestamp).total_seconds() / 3600,
        )
        # 100 now; decays linearly to zero after 30 days.
        return round(max(0.0, 100.0 * (1.0 - age_hours / 720.0)), 2)

    def _validate_indicator(self, indicator_key: str) -> None:
        result = (
            self.db.table("sews_indicator_definitions")
            .select("indicator_key")
            .eq("indicator_key", indicator_key)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise SEWSObservationError(
                f"Unknown indicator_key: {indicator_key}"
            )

    def create(
        self, request: ObservationCreateRequest
    ) -> ObservationResponse:
        self._validate_indicator(request.indicator_key)

        evidence_ids = [str(link.evidence_object_id) for link in request.evidence_links]
        evidence_result = (
            self.db.table("sews_evidence_objects")
            .select(
                "id,status,source_reliability,event_time,raw_evidence_id,"
                "sews_raw_evidence!inner(source_id)"
            )
            .in_("id", evidence_ids)
            .execute()
        )
        evidence_rows = evidence_result.data or []
        found_ids = {row["id"] for row in evidence_rows}
        missing = [item for item in evidence_ids if item not in found_ids]
        if missing:
            raise SEWSObservationError(
                f"Evidence objects not found: {', '.join(missing)}"
            )

        # Prevent duplicate observations for the same
        # evidence-object / indicator / warning combination.
        existing_links = (
            self.db.table(
                "sews_observation_evidence_links"
            )
            .select("observation_id,evidence_object_id")
            .in_("evidence_object_id", evidence_ids)
            .execute()
        )

        linked_observation_ids = {
            row["observation_id"]
            for row in (existing_links.data or [])
        }

        if linked_observation_ids:
            existing_query = (
                self.db.table("sews_observations")
                .select(
                    "id,observation_key,indicator_key,status,"
                    "evidence_count,corroborated_source_count,"
                    "source_reliability_mean,freshness_score,"
                    "warning_problem_key"
                )
                .in_("id", list(linked_observation_ids))
                .eq("indicator_key", request.indicator_key)
            )

            if request.warning_problem_key:
                existing_query = existing_query.eq(
                    "warning_problem_key",
                    request.warning_problem_key,
                )

            existing_result = (
                existing_query.limit(1).execute()
            )

            if existing_result.data:
                existing = existing_result.data[0]

                return ObservationResponse(
                    id=existing["id"],
                    observation_key=existing[
                        "observation_key"
                    ],
                    indicator_key=existing[
                        "indicator_key"
                    ],
                    status=existing["status"],
                    evidence_count=existing[
                        "evidence_count"
                    ],
                    corroborated_source_count=existing[
                        "corroborated_source_count"
                    ],
                    source_reliability_mean=existing.get(
                        "source_reliability_mean"
                    ),
                    freshness_score=existing.get(
                        "freshness_score"
                    ),
                )

        invalid = [
            row["id"]
            for row in evidence_rows
            if row["status"] not in {"NORMALIZED", "VALIDATED"}
        ]
        if invalid:
            raise SEWSObservationError(
                f"Evidence objects are not analytically usable: {', '.join(invalid)}"
            )

        source_ids = {
            row["sews_raw_evidence"]["source_id"]
            for row in evidence_rows
            if row.get("sews_raw_evidence")
        }
        reliability_values = [
            float(row["source_reliability"]) for row in evidence_rows
        ]
        freshness_values = [
            self._freshness_score(row.get("event_time"))
            for row in evidence_rows
        ]

        observation_key = f"OBS-{request.indicator_key}-{uuid4().hex}"
        observation = request.model_dump(
            mode="json",
            exclude={"evidence_links"},
            exclude_none=True,
        )
        observation.update(
            {
                "observation_key": observation_key,
                "evidence_count": len(evidence_rows),
                "corroborated_source_count": len(source_ids),
                "source_reliability_mean": round(mean(reliability_values), 2),
                "freshness_score": round(mean(freshness_values), 2),
            }
        )

        created_observation = (
            self.db.table("sews_observations").insert(observation).execute()
        )
        if not created_observation.data:
            raise SEWSObservationError("Observation insert returned no row.")
        created = created_observation.data[0]

        links = []
        for link in request.evidence_links:
            item = link.model_dump(mode="json")
            item["observation_id"] = created["id"]
            item["evidence_object_id"] = str(link.evidence_object_id)
            links.append(item)

        try:
            self.db.table("sews_observation_evidence_links").insert(
                links
            ).execute()
        except Exception:
            # Best-effort compensation because Supabase REST calls are not a
            # multi-statement transaction.
            self.db.table("sews_observations").delete().eq(
                "id", created["id"]
            ).execute()
            raise

        return ObservationResponse(
            id=created["id"],
            observation_key=created["observation_key"],
            indicator_key=created["indicator_key"],
            status=created["status"],
            evidence_count=created["evidence_count"],
            corroborated_source_count=created["corroborated_source_count"],
            source_reliability_mean=created.get("source_reliability_mean"),
            freshness_score=created.get("freshness_score"),
        )

    def list_observations(
        self,
        *,
        indicator_key: str | None = None,
        warning_problem_key: str | None = None,
        country_iso3: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        query = self.db.table("sews_observation_summary").select("*")
        if indicator_key:
            query = query.eq("indicator_key", indicator_key)
        if warning_problem_key:
            query = query.eq("warning_problem_key", warning_problem_key)
        if country_iso3:
            query = query.eq("country_iso3", country_iso3.upper())
        if status:
            query = query.eq("status", status)
        return (
            query.order("observed_at", desc=True).limit(limit).execute().data
            or []
        )
