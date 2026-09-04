from __future__ import annotations

from typing import Any

from .base import BaseCollector


class CisaAdvisoryCollector(BaseCollector):
    source_name = "CISA Cybersecurity Advisories"
    feed_url = "https://www.cisa.gov/cybersecurity-advisories/all.xml"

    async def collect(self, *, limit: int = 100) -> dict[str, Any]:
        # CISA's advisory feed is XML/RSS, so use httpx directly and parse with
        # Python's standard library to avoid adding another production dependency.
        import xml.etree.ElementTree as ET
        import httpx

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
                response = await client.get(self.feed_url, headers={"User-Agent": "SovereignIntelligenceAI/1.0"})
                response.raise_for_status()
        except httpx.HTTPError as exc:
            from .base import CollectorError
            raise CollectorError(f"{self.source_name} collection failed: {exc}") from exc

        root = ET.fromstring(response.text)
        items = root.findall(".//item")[: max(1, min(limit, 500))]
        collected_at = self.collected_at()
        records = []
        for item in items:
            record = {
                "title": item.findtext("title"),
                "url": item.findtext("link"),
                "published": item.findtext("pubDate"),
                "description": item.findtext("description"),
            }
            records.append({
                "source": "cisa_advisories",
                "record_type": "cybersecurity_advisory",
                "source_record_id": record["url"] or record["title"],
                **record,
                "provenance": {
                    "source_name": self.source_name,
                    "source_type": "government_cyber_advisory",
                    "source_url": record["url"] or self.feed_url,
                    "publisher": "Cybersecurity and Infrastructure Security Agency",
                    "collected_at": collected_at.isoformat(),
                    "source_record_id": record["url"] or record["title"],
                    "retrieval_method": "official_rss_feed",
                    "content_hash": self.stable_hash(record),
                    "reliability_score": 0.98,
                },
            })
        return {"source": "cisa_advisories", "count": len(records), "records": records}
