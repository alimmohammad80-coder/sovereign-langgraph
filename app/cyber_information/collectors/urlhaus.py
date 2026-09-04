from __future__ import annotations

from typing import Any

from .base import BaseCollector


class UrlhausCollector(BaseCollector):
    source_name = "URLhaus"
    recent_url = "https://urlhaus-api.abuse.ch/v1/urls/recent/"

    async def collect_recent(self, *, limit: int = 100) -> dict[str, Any]:
        payload = await self.get_json(self.recent_url)
        urls = payload.get("urls", [])[: max(1, min(limit, 1000))]
        collected_at = self.collected_at()
        records = []
        for item in urls:
            records.append({
                "source": "urlhaus",
                "record_type": "malware_distribution_infrastructure",
                "source_record_id": str(item.get("id") or item.get("url")),
                "url": item.get("url"),
                "url_status": item.get("url_status"),
                "host": item.get("host"),
                "date_added": item.get("date_added"),
                "threat": item.get("threat"),
                "tags": item.get("tags") or [],
                "reporter": item.get("reporter"),
                "provenance": {
                    "source_name": self.source_name,
                    "source_type": "community_malware_infrastructure_feed",
                    "source_url": "https://urlhaus.abuse.ch/",
                    "publisher": "abuse.ch",
                    "collected_at": collected_at.isoformat(),
                    "source_record_id": str(item.get("id") or item.get("url")),
                    "retrieval_method": "urlhaus_api",
                    "content_hash": self.stable_hash(item),
                    "reliability_score": 0.86,
                },
            })
        return {"source": "urlhaus", "count": len(records), "records": records}
