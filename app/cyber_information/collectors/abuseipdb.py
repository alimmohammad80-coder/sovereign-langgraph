from __future__ import annotations

import os
from typing import Any

from .base import BaseCollector, CollectorError


class AbuseIpDbCollector(BaseCollector):
    source_name = "AbuseIPDB"
    check_url = "https://api.abuseipdb.com/api/v2/check"

    async def check(self, *, ip_address: str, max_age_days: int = 90) -> dict[str, Any]:
        api_key = os.getenv("ABUSEIPDB_API_KEY")
        if not api_key:
            raise CollectorError("ABUSEIPDB_API_KEY is not configured")
        payload = await self.get_json(
            self.check_url,
            params={"ipAddress": ip_address, "maxAgeInDays": max(1, min(max_age_days, 365)), "verbose": "true"},
            headers={"Key": api_key},
        )
        item = payload.get("data", {})
        collected_at = self.collected_at()
        record = {
            "source": "abuseipdb",
            "record_type": "ip_reputation",
            "source_record_id": item.get("ipAddress") or ip_address,
            "ip_address": item.get("ipAddress") or ip_address,
            "is_public": item.get("isPublic"),
            "ip_version": item.get("ipVersion"),
            "abuse_confidence_score": item.get("abuseConfidenceScore"),
            "country_code": item.get("countryCode"),
            "usage_type": item.get("usageType"),
            "isp": item.get("isp"),
            "domain": item.get("domain"),
            "total_reports": item.get("totalReports"),
            "last_reported_at": item.get("lastReportedAt"),
            "provenance": {
                "source_name": self.source_name,
                "source_type": "ip_reputation_service",
                "source_url": self.check_url,
                "publisher": "AbuseIPDB",
                "collected_at": collected_at.isoformat(),
                "source_record_id": item.get("ipAddress") or ip_address,
                "retrieval_method": "abuseipdb_api_v2",
                "content_hash": self.stable_hash(item),
                "reliability_score": 0.78,
            },
        }
        return {"source": "abuseipdb", "count": 1, "records": [record]}
