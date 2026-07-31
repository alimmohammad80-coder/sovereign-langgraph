from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from supabase import Client

from app.schemas.sews_evidence import (
    EvidenceIngestRequest,
    EvidenceIngestResponse,
    EvidenceNormalizeRequest,
    EvidenceObjectResponse,
)


class SEWSEvidenceError(RuntimeError):
    pass


class SEWSEvidenceService:
    def __init__(self, db: Client):
        self.db = db

    @staticmethod
    def _canonical_content(payload: EvidenceIngestRequest) -> str:
        parts = [
            payload.title or "",
            payload.raw_text or "",
            json.dumps(payload.raw_payload, sort_keys=True, default=str)
            if payload.raw_payload is not None
            else "",
            str(payload.canonical_url or ""),
            payload.source_external_id or "",
        ]
        content = "\n".join(parts).strip()
        if not content:
            raise SEWSEvidenceError(
                "Evidence must include raw_text, raw_payload, title, URL, or external ID."
            )
        return content

    @staticmethod
    def _content_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _source(self, source_key: str) -> dict[str, Any]:
        response = (
            self.db.table("sews_sources")
            .select("id,source_key,status,default_reliability")
            .eq("source_key", source_key)
            .limit(1)
            .execute()
        )
        if not response.data:
            raise SEWSEvidenceError(f"Unknown SEWS source: {source_key}")
        source = response.data[0]
        if source["status"] not in {"ACTIVE", "DEGRADED"}:
            raise SEWSEvidenceError(
                f"SEWS source {source_key} is not available: {source['status']}"
            )
        return source

    def ingest(self, request: EvidenceIngestRequest) -> EvidenceIngestResponse:
        source = self._source(request.source_key)
        content = self._canonical_content(request)
        content_hash = self._content_hash(content)

        duplicate_query = (
            self.db.table("sews_raw_evidence")
            .select("id,evidence_key,status")
            .eq("source_id", source["id"])
        )
        if request.source_external_id:
            duplicate_query = duplicate_query.eq(
                "source_external_id", request.source_external_id
            )
        else:
            duplicate_query = duplicate_query.eq("content_hash", content_hash)

        duplicate = duplicate_query.limit(1).execute()
        if duplicate.data:
            row = duplicate.data[0]
            return EvidenceIngestResponse(
                id=row["id"],
                evidence_key=row["evidence_key"],
                duplicate=True,
                status=row["status"],
            )

        evidence_key = f"RAW-{request.source_key}-{uuid4().hex}"
        row = request.model_dump(
            exclude={"source_key"},
            mode="json",
            exclude_none=True,
        )
        if row.get("canonical_url") is not None:
            row["canonical_url"] = str(row["canonical_url"])

        row.update(
            {
                "evidence_key": evidence_key,
                "source_id": source["id"],
                "content_hash": content_hash,
                "status": "RAW",
                "collected_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        response = self.db.table("sews_raw_evidence").insert(row).execute()
        if not response.data:
            raise SEWSEvidenceError("Raw evidence insert returned no row.")

        created = response.data[0]
        return EvidenceIngestResponse(
            id=created["id"],
            evidence_key=created["evidence_key"],
            duplicate=False,
            status=created["status"],
        )

    def normalize(
        self, request: EvidenceNormalizeRequest
    ) -> EvidenceObjectResponse:
        raw_result = (
            self.db.table("sews_raw_evidence")
            .select("id,status,country_iso3,region_key,observed_at,published_at")
            .eq("id", str(request.raw_evidence_id))
            .limit(1)
            .execute()
        )
        if not raw_result.data:
            raise SEWSEvidenceError(
                f"Raw evidence not found: {request.raw_evidence_id}"
            )
        raw = raw_result.data[0]
        if raw["status"] in {"REJECTED", "ARCHIVED"}:
            raise SEWSEvidenceError(
                f"Cannot normalize raw evidence with status {raw['status']}."
            )

        existing = (
            self.db.table("sews_evidence_objects")
            .select("id,evidence_object_key,raw_evidence_id,status")
            .eq("raw_evidence_id", str(request.raw_evidence_id))
            .eq("evidence_type", request.evidence_type)
            .limit(1)
            .execute()
        )
        if existing.data:
            row = existing.data[0]
            return EvidenceObjectResponse(**row)

        row = request.model_dump(mode="json", exclude_none=True)
        row["raw_evidence_id"] = str(request.raw_evidence_id)
        row["evidence_object_key"] = f"EVO-{uuid4().hex}"
        row["status"] = (
            "VALIDATED"
            if request.validation_confidence is not None
            and request.validation_confidence >= 60
            else "NORMALIZED"
        )
        row.setdefault("event_time", raw.get("observed_at") or raw.get("published_at"))
        row.setdefault("country_iso3", raw.get("country_iso3"))
        row.setdefault("region_key", raw.get("region_key"))

        response = self.db.table("sews_evidence_objects").insert(row).execute()
        if not response.data:
            raise SEWSEvidenceError("Evidence normalization returned no row.")

        self.db.table("sews_raw_evidence").update(
            {"status": "NORMALIZED"}
        ).eq("id", str(request.raw_evidence_id)).execute()

        created = response.data[0]
        return EvidenceObjectResponse(
            id=created["id"],
            evidence_object_key=created["evidence_object_key"],
            raw_evidence_id=created["raw_evidence_id"],
            status=created["status"],
        )

    def list_evidence(
        self,
        *,
        source_key: str | None = None,
        country_iso3: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        query = self.db.table("sews_raw_evidence").select(
            "*,sews_sources!inner(source_key,name)"
        )
        if source_key:
            query = query.eq("sews_sources.source_key", source_key)
        if country_iso3:
            query = query.eq("country_iso3", country_iso3.upper())
        if status:
            query = query.eq("status", status)
        response = query.order("collected_at", desc=True).limit(limit).execute()
        return response.data or []
