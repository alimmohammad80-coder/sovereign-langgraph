from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from statistics import mean
from typing import Any

from supabase import Client


class SEWSEvidenceContextService:
    """Build canonical warning-level evidence context from explicit DB links.

    The service never joins observations to evidence by title. It follows the
    authoritative chain:
      sews_observations -> sews_observation_evidence_links ->
      sews_evidence_objects -> sews_raw_evidence -> sews_sources
    """

    def __init__(self, db: Client):
        self.db = db

    @staticmethod
    def _iso(value: Any) -> str | None:
        if value is None:
            return None
        return str(value)

    @staticmethod
    def _freshness_score(timestamp: str | None) -> float | None:
        if not timestamp:
            return None
        try:
            dt = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            hours = max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 3600)
            return round(max(0.0, 100.0 * (1.0 - hours / 720.0)), 2)
        except Exception:
            return None

    def build(self, problem_key: str, *, limit: int = 100) -> dict[str, Any]:
        observations = (
            self.db.table("sews_observations")
            .select(
                "id,observation_key,indicator_key,warning_problem_key,status,"
                "statement,observed_at,evidence_count,corroborated_source_count,"
                "source_reliability_mean,freshness_score"
            )
            .eq("warning_problem_key", problem_key)
            .order("observed_at", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )

        if not observations:
            return {
                "problem_key": problem_key,
                "documents": [],
                "quality": {
                    "document_count": 0,
                    "linked_observation_count": 0,
                    "unique_source_count": 0,
                    "mean_reliability": None,
                    "mean_freshness": None,
                    "validated_document_count": 0,
                },
            }

        observation_by_id = {str(row["id"]): row for row in observations}
        observation_ids = list(observation_by_id)

        links = (
            self.db.table("sews_observation_evidence_links")
            .select("observation_id,evidence_object_id,relationship_type,weight,notes")
            .in_("observation_id", observation_ids)
            .execute()
            .data
            or []
        )

        evidence_object_ids = sorted(
            {str(row["evidence_object_id"]) for row in links if row.get("evidence_object_id")}
        )
        if not evidence_object_ids:
            return {
                "problem_key": problem_key,
                "documents": [],
                "quality": {
                    "document_count": 0,
                    "linked_observation_count": len(observations),
                    "unique_source_count": 0,
                    "mean_reliability": None,
                    "mean_freshness": None,
                    "validated_document_count": 0,
                },
            }

        evidence_objects = (
            self.db.table("sews_evidence_objects")
            .select(
                "id,raw_evidence_id,evidence_object_key,evidence_type,status,event_time,"
                "source_reliability,validation_confidence,country_iso3,region_key"
            )
            .in_("id", evidence_object_ids)
            .execute()
            .data
            or []
        )
        evidence_by_id = {str(row["id"]): row for row in evidence_objects}

        raw_ids = sorted(
            {str(row["raw_evidence_id"]) for row in evidence_objects if row.get("raw_evidence_id")}
        )
        raw_rows = []
        if raw_ids:
            raw_rows = (
                self.db.table("sews_raw_evidence")
                .select(
                    "id,evidence_key,source_id,source_external_id,title,raw_text,canonical_url,"
                    "published_at,observed_at,collected_at,status,country_iso3,region_key,"
                    "sews_sources(source_key,name,status,default_reliability)"
                )
                .in_("id", raw_ids)
                .execute()
                .data
                or []
            )
        raw_by_id = {str(row["id"]): row for row in raw_rows}

        links_by_evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for link in links:
            eid = str(link.get("evidence_object_id") or "")
            oid = str(link.get("observation_id") or "")
            if eid and oid and oid in observation_by_id:
                links_by_evidence[eid].append({**link, "observation": observation_by_id[oid]})

        documents: list[dict[str, Any]] = []
        for evidence_id in evidence_object_ids:
            evo = evidence_by_id.get(evidence_id)
            if not evo:
                continue
            raw = raw_by_id.get(str(evo.get("raw_evidence_id") or ""), {})
            source = raw.get("sews_sources") or {}
            if isinstance(source, list):
                source = source[0] if source else {}

            linked = links_by_evidence.get(evidence_id, [])
            indicator_keys = sorted(
                {
                    str(item["observation"].get("indicator_key"))
                    for item in linked
                    if item["observation"].get("indicator_key")
                }
            )
            observation_keys = sorted(
                {
                    str(item["observation"].get("observation_key"))
                    for item in linked
                    if item["observation"].get("observation_key")
                }
            )
            statements = [
                str(item["observation"].get("statement"))
                for item in linked
                if item["observation"].get("statement")
            ]

            timestamp = (
                evo.get("event_time")
                or raw.get("published_at")
                or raw.get("observed_at")
                or raw.get("collected_at")
            )
            reliability = evo.get("source_reliability")
            if reliability is None:
                reliability = source.get("default_reliability")

            documents.append(
                {
                    "evidence_object_id": evidence_id,
                    "evidence_object_key": evo.get("evidence_object_key"),
                    "raw_evidence_id": evo.get("raw_evidence_id"),
                    "raw_evidence_key": raw.get("evidence_key"),
                    "source_external_id": raw.get("source_external_id"),
                    "source_key": source.get("source_key"),
                    "source_name": source.get("name") or source.get("source_key"),
                    "source_status": source.get("status"),
                    "title": raw.get("title"),
                    "summary": raw.get("raw_text") or (statements[0] if statements else None),
                    "url": raw.get("canonical_url"),
                    "published_at": raw.get("published_at"),
                    "event_time": evo.get("event_time") or raw.get("observed_at"),
                    "collected_at": raw.get("collected_at"),
                    "status": evo.get("status"),
                    "evidence_type": evo.get("evidence_type"),
                    "reliability": float(reliability) if reliability is not None else None,
                    "validation_confidence": (
                        float(evo["validation_confidence"])
                        if evo.get("validation_confidence") is not None
                        else None
                    ),
                    "freshness": self._freshness_score(self._iso(timestamp)),
                    "country_iso3": evo.get("country_iso3") or raw.get("country_iso3"),
                    "region_key": evo.get("region_key") or raw.get("region_key"),
                    "indicator_keys": indicator_keys,
                    "observation_keys": observation_keys,
                    "observation_count": len(linked),
                    "observation_statements": statements[:6],
                }
            )

        def sort_key(row: dict[str, Any]) -> tuple[float, float, str]:
            validated = 1.0 if str(row.get("status") or "").upper() == "VALIDATED" else 0.0
            reliability = float(row.get("reliability") or 0)
            timestamp = str(row.get("published_at") or row.get("event_time") or row.get("collected_at") or "")
            return (validated, reliability, timestamp)

        documents.sort(key=sort_key, reverse=True)

        reliabilities = [float(row["reliability"]) for row in documents if row.get("reliability") is not None]
        freshness_values = [float(row["freshness"]) for row in documents if row.get("freshness") is not None]
        source_keys = {
            str(row.get("source_key") or row.get("source_name"))
            for row in documents
            if row.get("source_key") or row.get("source_name")
        }

        return {
            "problem_key": problem_key,
            "documents": documents[:limit],
            "quality": {
                "document_count": len(documents),
                "linked_observation_count": len(observations),
                "unique_source_count": len(source_keys),
                "mean_reliability": round(mean(reliabilities), 2) if reliabilities else None,
                "mean_freshness": round(mean(freshness_values), 2) if freshness_values else None,
                "validated_document_count": sum(
                    1 for row in documents if str(row.get("status") or "").upper() == "VALIDATED"
                ),
            },
        }
