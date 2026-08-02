from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any

from supabase import Client


class SEWSEvidenceDeduplicationService:
    DUPLICATE_THRESHOLD = 0.88

    def __init__(self, db: Client):
        self.db = db

    @staticmethod
    def _cluster_key(canonical_id: str) -> str:
        digest = hashlib.sha256(canonical_id.encode()).hexdigest()[:16]
        return f"SEWS-CLUSTER-{digest}".upper()

    def _rows(self, problem_key: str) -> list[dict[str, Any]]:
        result = (
            self.db.table("sews_raw_evidence")
            .select(
                "id,title,raw_text,source_id,published_at,collected_at,"
                "embedding,duplicate_of_id,metadata"
            )
            .contains(
                "metadata",
                {"warning_problem_key": problem_key},
            )
            .not_.is_("embedding", "null")
            .order("published_at")
            .limit(500)
            .execute()
        )
        return result.data or []

    def _similar(self, embedding: list[float]) -> list[dict[str, Any]]:
        result = self.db.rpc(
            "match_sews_evidence",
            {
                "query_embedding": embedding,
                "match_threshold": self.DUPLICATE_THRESHOLD,
                "match_count": 100,
            },
        ).execute()
        return result.data or []

    def run(self, problem_key: str) -> dict[str, Any]:
        rows = self._rows(problem_key)

        if not rows:
            return {
                "problem_key": problem_key,
                "records_considered": 0,
                "clusters_created": 0,
                "duplicates_marked": 0,
            }

        by_id = {str(row["id"]): row for row in rows}
        assigned: set[str] = set()
        clusters: list[list[str]] = []

        for row in rows:
            row_id = str(row["id"])

            if row_id in assigned:
                continue

            cluster = [row_id]
            assigned.add(row_id)

            for candidate in self._similar(row["embedding"]):
                candidate_id = str(candidate["id"])

                if candidate_id == row_id:
                    continue

                if candidate_id not in by_id:
                    continue

                if candidate_id in assigned:
                    continue

                cluster.append(candidate_id)
                assigned.add(candidate_id)

            clusters.append(cluster)

        duplicates_marked = 0
        cluster_summaries = []

        for member_ids in clusters:
            members = [by_id[item] for item in member_ids]

            canonical = sorted(
                members,
                key=lambda item: (
                    item.get("published_at")
                    or item.get("collected_at")
                    or ""
                ),
            )[0]

            canonical_id = str(canonical["id"])
            cluster_key = self._cluster_key(canonical_id)

            source_ids = {
                str(item["source_id"])
                for item in members
                if item.get("source_id")
            }

            corroboration_count = len(members)
            source_diversity_count = len(source_ids)

            for member in members:
                member_id = str(member["id"])
                metadata = dict(member.get("metadata") or {})

                metadata.update(
                    {
                        "duplicate_cluster_key": cluster_key,
                        "canonical_evidence_id": canonical_id,
                        "corroboration_count": corroboration_count,
                        "source_diversity_count": source_diversity_count,
                        "deduplication_version": "sews-semantic-dedup-v1",
                    }
                )

                update = {
                    "metadata": metadata,
                    "duplicate_of_id": (
                        None
                        if member_id == canonical_id
                        else canonical_id
                    ),
                }

                (
                    self.db.table("sews_raw_evidence")
                    .update(update)
                    .eq("id", member_id)
                    .execute()
                )

                if member_id != canonical_id:
                    duplicates_marked += 1

            evidence_objects = (
                self.db.table("sews_evidence_objects")
                .select("id,raw_evidence_id,attributes")
                .in_("raw_evidence_id", member_ids)
                .execute()
                .data
                or []
            )

            for evidence_object in evidence_objects:
                attributes = dict(
                    evidence_object.get("attributes") or {}
                )
                attributes.update(
                    {
                        "canonical_evidence_id": canonical_id,
                        "source_diversity_count": source_diversity_count,
                        "deduplication_version": "sews-semantic-dedup-v1",
                    }
                )

                (
                    self.db.table("sews_evidence_objects")
                    .update(
                        {
                            "duplicate_cluster_key": cluster_key,
                            "corroboration_count": corroboration_count,
                            "attributes": attributes,
                        }
                    )
                    .eq("id", evidence_object["id"])
                    .execute()
                )

            cluster_summaries.append(
                {
                    "cluster_key": cluster_key,
                    "canonical_evidence_id": canonical_id,
                    "member_count": corroboration_count,
                    "source_diversity_count": source_diversity_count,
                }
            )

        return {
            "problem_key": problem_key,
            "records_considered": len(rows),
            "clusters_created": len(clusters),
            "duplicates_marked": duplicates_marked,
            "clusters": cluster_summaries,
        }
