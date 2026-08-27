from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)

from app.services.conflict_intelligence.conflict_evidence_enricher import (
    ConflictEvidenceEnricher,
)


class ConflictNewsEvidenceBridge:

    def __init__(self) -> None:
        self.db = get_supabase_client()
        self.enricher = ConflictEvidenceEnricher()

    @staticmethod
    def _evidence_key(
        event: dict[str, Any],
        conflict_id: int,
    ) -> str:

        url = str(
            event.get("url")
            or ""
        ).strip().lower()

        title = str(
            event.get("title")
            or ""
        ).strip().lower()

        canonical_source = (
            url
            or title
        )

        raw = "|".join(
            [
                str(conflict_id),
                canonical_source,
                str(
                    event.get("published_at")
                    or ""
                ),
            ]
        )

        digest = hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest()[:24].upper()

        return f"CEV-{digest}"

    def _events(
        self,
        *,
        limit: int,
    ) -> list[dict[str, Any]]:

        rows = (
            self.db.table("news_events")
            .select("*")
            .eq("is_approved", True)
            .order("published_at", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )

        unique = []
        seen = set()

        for row in rows:

            key = (
                str(
                    row.get("url")
                    or ""
                ).strip().lower()
                or str(
                    row.get("title")
                    or ""
                ).strip().lower()
            )

            if not key:
                continue

            if key in seen:
                continue

            seen.add(key)
            unique.append(row)

        return unique

    def run(
        self,
        *,
        limit: int = 500,
    ) -> dict[str, Any]:

        events = self._events(
            limit=limit
        )

        matched = 0
        stored = 0
        skipped = 0
        errors = []

        now = datetime.now(
            timezone.utc
        ).isoformat()

        for event in events:

            try:
                enriched = (
                    self.enricher.enrich(
                        event
                    )
                )

                if not enriched["matched"]:
                    skipped += 1
                    continue

                conflict_id = int(
                    enriched["conflict_id"]
                )

                key = self._evidence_key(
                    event,
                    conflict_id,
                )

                matched += 1

                record = {
                    "evidence_key":
                        key,

                    "conflict_id":
                        conflict_id,

                    "canonical_episode_id":
                        enriched.get(
                            "canonical_episode_id"
                        ),

                    "evidence_type":
                        "news_event",

                    "event_type":
                        enriched.get(
                            "event_type"
                        ),

                    "title":
                        event.get("title"),

                    "summary":
                        event.get("summary"),

                    "observed_at":
                        event.get("published_at"),

                    "published_at":
                        event.get("published_at"),

                    "countries":
                        enriched.get(
                            "countries"
                        )
                        or [],

                    "actors":
                        [],

                    "territories":
                        [
                            str(
                                x.get("name")
                                if isinstance(x, dict)
                                else x
                            )
                            for x in (
                                enriched.get(
                                    "territories"
                                )
                                or []
                            )
                            if x
                        ],

                    "severity":
                        enriched.get(
                            "severity"
                        ),

                    "confidence":
                        enriched.get(
                            "confidence"
                        ),

                    "source_name":
                        event.get(
                            "source_name"
                        ),

                    # Legacy required column retained
                    # for compatibility with the existing
                    # conflict_evidence table.
                    "source":
                        event.get(
                            "source_name"
                        )
                        or "unknown",

                    "source_url":
                        event.get("url"),

                    "source_type":
                        "news",

                    "source_reliability":
                        enriched.get(
                            "source_reliability"
                        ),

                    "citation_text":
                        enriched.get(
                            "citation_text"
                        ),

                    "supports_escalation":
                        enriched.get(
                            "supports_escalation"
                        ),

                    "contradicts_escalation":
                        enriched.get(
                            "contradicts_escalation"
                        ),

                    "raw_payload":
                        {
                            "news_event_id":
                                event.get("id"),

                            "topic_tags":
                                event.get(
                                    "topic_tags"
                                )
                                or [],

                            "region":
                                event.get("region"),

                            "credibility_score":
                                event.get(
                                    "credibility_score"
                                ),

                            "matcher":
                                enriched.get(
                                    "match_details"
                                ),

                            "classifier":
                                enriched.get(
                                    "classification_details"
                                ),
                        },

                    "active":
                        True,

                    "review_status":
                        "provisional",

                    "updated_at":
                        now,
                }

                (
                    self.db.table(
                        "conflict_evidence"
                    )
                    .upsert(
                        record,
                        on_conflict="evidence_key",
                    )
                    .execute()
                )

                stored += 1

            except Exception as exc:
                errors.append(
                    {
                        "event_id":
                            event.get("id"),

                        "error":
                            (
                                f"{type(exc).__name__}: "
                                f"{exc}"
                            ),
                    }
                )

        return {
            "status": "success",
            "events_checked": len(events),
            "matched": matched,
            "stored": stored,
            "skipped": skipped,
            "error_count": len(errors),
            "errors": errors[:20],
        }
