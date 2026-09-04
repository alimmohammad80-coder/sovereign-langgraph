from __future__ import annotations

from typing import Any

import feedparser
import httpx

from .base import BaseCollector, CollectorError


OFFICIAL_CERT_FEEDS: dict[str, dict[str, str]] = {
    "uk_ncsc_threat_reports": {
        "name": "UK National Cyber Security Centre Threat Reports",
        "publisher": "UK National Cyber Security Centre",
        "url": "https://www.ncsc.gov.uk/api/1/services/v1/report-rss-feed.xml",
        "country_iso3": "GBR",
    },
    "canada_cyber_alerts": {
        "name": "Canadian Centre for Cyber Security Alerts and Advisories",
        "publisher": "Canadian Centre for Cyber Security",
        "url": "https://www.cyber.gc.ca/api/cccs/rss/v1/get?feed=alerts_advisories&lang=en",
        "country_iso3": "CAN",
    },
}


class CertFeedCollector(BaseCollector):
    source_name = "National CERT/CSIRT Feed"

    async def collect_registered(self, *, feed_id: str, limit: int = 100) -> dict[str, Any]:
        config = OFFICIAL_CERT_FEEDS.get(feed_id)
        if not config:
            raise CollectorError(f"unknown CERT/CSIRT feed: {feed_id}")
        return await self.collect_url(
            url=config["url"],
            source_name=config["name"],
            publisher=config["publisher"],
            country_iso3=config.get("country_iso3"),
            limit=limit,
            feed_id=feed_id,
        )

    async def collect_url(
        self,
        *,
        url: str,
        source_name: str,
        publisher: str,
        country_iso3: str | None = None,
        limit: int = 100,
        feed_id: str | None = None,
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": "SovereignIntelligenceAI/1.0 cyber-information-collector"},
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise CollectorError(f"{source_name} collection failed: {exc}") from exc

        parsed = feedparser.parse(response.content)
        if getattr(parsed, "bozo", False) and not parsed.entries:
            raise CollectorError(f"{source_name} returned an unreadable RSS/Atom feed")

        collected_at = self.collected_at()
        records = []
        for entry in parsed.entries[: max(1, min(limit, 500))]:
            record = {
                "title": entry.get("title"),
                "url": entry.get("link"),
                "published": entry.get("published") or entry.get("updated"),
                "summary": entry.get("summary") or entry.get("description"),
                "author": entry.get("author"),
                "tags": [tag.get("term") for tag in entry.get("tags", []) if tag.get("term")],
            }
            source_record_id = entry.get("id") or record["url"] or record["title"]
            records.append({
                "source": feed_id or "cert_csirt",
                "record_type": "cert_csirt_advisory",
                "source_record_id": source_record_id,
                "country_iso3": country_iso3,
                **record,
                "provenance": {
                    "source_name": source_name,
                    "source_type": "national_cert_csirt_feed",
                    "source_url": record["url"] or url,
                    "publisher": publisher,
                    "collected_at": collected_at.isoformat(),
                    "source_record_id": source_record_id,
                    "retrieval_method": "official_rss_atom_feed",
                    "content_hash": self.stable_hash(record),
                    "reliability_score": 0.97,
                },
            })
        return {
            "source": feed_id or source_name,
            "feed_url": url,
            "country_iso3": country_iso3,
            "count": len(records),
            "records": records,
        }


def cert_feed_registry() -> dict[str, dict[str, str]]:
    return OFFICIAL_CERT_FEEDS.copy()
