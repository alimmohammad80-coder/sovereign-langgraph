from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Any

from app.repositories.conflict_intelligence_repository import (
    get_supabase_client,
)

from app.services.sovereign_news_ingestion import (
    generate_news_signals,
)

from app.services.gdelt_service import (
    fetch_gdelt_news,
)

from app.services.conflict_intelligence.conflict_news_evidence_bridge import (
    ConflictNewsEvidenceBridge,
)


class ConflictCollectionOrchestrator:

    def __init__(self) -> None:
        self.db = get_supabase_client()

    @staticmethod
    def _event_key(
        *,
        source_name: str,
        title: str,
        url: str | None,
        published_at: str | None,
    ) -> str:

        raw = "|".join(
            [
                source_name or "",
                title or "",
                url or "",
                published_at or "",
            ]
        )

        digest = hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest()[:24].upper()

        return f"NEWS-{digest}"

    @staticmethod
    def _normalize_signal(
        item: dict[str, Any],
    ) -> dict[str, Any]:

        source_name = (
            item.get("source")
            or item.get("source_name")
            or item.get("domain")
            or "Unknown"
        )

        published_at = (
            item.get("published_at")
            or item.get("seendate")
            or item.get("created_at")
        )

        title = str(
            item.get("title")
            or ""
        )

        summary = str(
            item.get("summary")
            or item.get("description")
            or ""
        )

        url = (
            item.get("url")
            or ""
        )

        credibility = item.get(
            "source_quality"
        )

        if credibility is None:
            credibility_score = 7
        else:
            credibility_score = min(
                10,
                max(
                    1,
                    round(
                        5
                        + float(credibility) / 5
                    ),
                ),
            )

        return {
            "source_name":
                source_name,

            "domain":
                item.get("domain"),

            "title":
                title,

            "summary":
                summary,

            "url":
                url,

            "language":
                "en",

            "country_code":
                None,

            "country_name":
                None,

            "region":
                None,

            "topic_tags":
                item.get("drivers")
                or [],

            "credibility_score":
                credibility_score,

            "is_approved":
                True,

            "published_at":
                published_at,

            "created_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

        }

    def _upsert_news_event(
        self,
        item: dict[str, Any],
    ) -> bool:

        row = self._normalize_signal(
            item
        )

        url = str(
            row.get("url")
            or ""
        ).strip()

        title = str(
            row.get("title")
            or ""
        ).strip()

        # news_events has no dedicated idempotency_key.
        # Use canonical URL first, then exact title as fallback.
        existing = []

        if url:
            existing = (
                self.db.table(
                    "news_events"
                )
                .select("id")
                .eq("url", url)
                .limit(1)
                .execute()
                .data
                or []
            )

        if (
            not existing
            and title
        ):
            existing = (
                self.db.table(
                    "news_events"
                )
                .select("id")
                .eq("title", title)
                .limit(1)
                .execute()
                .data
                or []
            )

        if existing:
            (
                self.db.table(
                    "news_events"
                )
                .update(row)
                .eq(
                    "id",
                    existing[0]["id"],
                )
                .execute()
            )
        else:
            (
                self.db.table(
                    "news_events"
                )
                .insert(row)
                .execute()
            )

        return True

    async def _collect_news(
        self,
        query: str,
        limit: int,
    ) -> list[dict[str, Any]]:

        result = await generate_news_signals(
            query=query,
            limit=limit,
        )

        return (
            result.get("signals")
            or []
        )

    @staticmethod
    def _collect_gdelt(
        query: str,
        limit: int,
    ) -> list[dict[str, Any]]:

        result = fetch_gdelt_news(
            query=query,
            max_records=limit,
        )

        if not isinstance(
            result,
            dict,
        ):
            return []

        return (
            result.get("articles")
            or []
        )

    async def run(
        self,
        *,
        query: str,
        limit_per_source: int = 25,
        evidence_limit: int = 500,
    ) -> dict[str, Any]:

        news_task = self._collect_news(
            query,
            limit_per_source,
        )

        gdelt_task = asyncio.to_thread(
            self._collect_gdelt,
            query,
            limit_per_source,
        )

        news_items, gdelt_items = (
            await asyncio.gather(
                news_task,
                gdelt_task,
            )
        )

        combined = (
            list(news_items)
            + list(gdelt_items)
        )

        stored_news_events = 0
        storage_errors = []

        for item in combined:
            try:
                if self._upsert_news_event(
                    item
                ):
                    stored_news_events += 1

            except Exception as exc:
                storage_errors.append(
                    {
                        "title":
                            item.get("title"),

                        "error":
                            (
                                f"{type(exc).__name__}: "
                                f"{exc}"
                            ),
                    }
                )

        evidence_result = (
            ConflictNewsEvidenceBridge()
            .run(
                limit=evidence_limit
            )
        )

        return {
            "status":
                "success",

            "query":
                query,

            "collected":
                {
                    "newsapi_google":
                        len(news_items),

                    "gdelt":
                        len(gdelt_items),

                    "total":
                        len(combined),
                },

            "news_events_stored":
                stored_news_events,

            "storage_error_count":
                len(storage_errors),

            "storage_errors":
                storage_errors[:20],

            "evidence_pipeline":
                evidence_result,
        }
