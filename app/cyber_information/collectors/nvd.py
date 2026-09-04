from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from .base import BaseCollector


class NvdCollector(BaseCollector):
    source_name = "NIST National Vulnerability Database"
    api_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"

    async def collect_recent(self, *, hours: int = 24, limit: int = 100) -> dict[str, Any]:
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=max(1, min(hours, 120)))
        params = {
            "lastModStartDate": start.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "lastModEndDate": end.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "resultsPerPage": max(1, min(limit, 2000)),
        }
        headers = {}
        if api_key := os.getenv("NVD_API_KEY"):
            headers["apiKey"] = api_key

        payload = await self.get_json(self.api_url, params=params, headers=headers)
        collected_at = self.collected_at()
        records = []
        for wrapper in payload.get("vulnerabilities", []):
            cve = wrapper.get("cve", {})
            descriptions = cve.get("descriptions", [])
            english = next((d.get("value") for d in descriptions if d.get("lang") == "en"), None)
            metrics = cve.get("metrics", {})
            records.append(
                {
                    "source": "nvd",
                    "record_type": "vulnerability",
                    "source_record_id": cve.get("id"),
                    "published": cve.get("published"),
                    "last_modified": cve.get("lastModified"),
                    "status": cve.get("vulnStatus"),
                    "description": english,
                    "weaknesses": cve.get("weaknesses", []),
                    "references": cve.get("references", []),
                    "metrics": metrics,
                    "provenance": {
                        "source_name": self.source_name,
                        "source_type": "government_vulnerability_database",
                        "source_url": self.api_url,
                        "publisher": "National Institute of Standards and Technology",
                        "collected_at": collected_at.isoformat(),
                        "source_record_id": cve.get("id"),
                        "retrieval_method": "nvd_cves_api_2_0",
                        "content_hash": self.stable_hash(cve),
                        "reliability_score": 0.97,
                    },
                }
            )
        return {"source": "nvd", "count": len(records), "records": records}
