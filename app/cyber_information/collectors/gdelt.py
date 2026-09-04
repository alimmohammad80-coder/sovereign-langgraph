from __future__ import annotations

from typing import Any

from .base import BaseCollector


class GdeltCollector(BaseCollector):
    source_name = "GDELT Project DOC 2.0"
    api_url = "https://api.gdeltproject.org/api/v2/doc/doc"

    async def search(self, *, query: str, max_records: int = 50) -> dict[str, Any]:
        params = {
            "query": query,
            "mode": "artlist",
            "maxrecords": max(1, min(max_records, 250)),
            "format": "json",
            "sort": "datedesc",
        }
        payload = await self.get_json(self.api_url, params=params)
        collected_at = self.collected_at()
        records = []
        for article in payload.get("articles", []):
            records.append(
                {
                    "source": "gdelt",
                    "record_type": "information_environment_observation",
                    "source_record_id": article.get("url"),
                    "title": article.get("title"),
                    "url": article.get("url"),
                    "domain": article.get("domain"),
                    "language": article.get("language"),
                    "source_country": article.get("sourcecountry"),
                    "seen_date": article.get("seendate"),
                    "social_image": article.get("socialimage"),
                    "provenance": {
                        "source_name": self.source_name,
                        "source_type": "global_news_event_index",
                        "source_url": article.get("url") or self.api_url,
                        "publisher": article.get("domain"),
                        "collected_at": collected_at.isoformat(),
                        "source_record_id": article.get("url"),
                        "retrieval_method": "gdelt_doc_api_v2",
                        "content_hash": self.stable_hash(article),
                        "reliability_score": 0.72,
                    },
                }
            )
        return {"source": "gdelt", "query": query, "count": len(records), "records": records}
