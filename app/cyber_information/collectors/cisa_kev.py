from __future__ import annotations

from typing import Any

from .base import BaseCollector


class CisaKevCollector(BaseCollector):
    source_name = "CISA Known Exploited Vulnerabilities"
    catalog_url = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

    async def collect(self, *, limit: int = 100) -> dict[str, Any]:
        payload = await self.get_json(self.catalog_url)
        vulnerabilities = payload.get("vulnerabilities", [])[: max(1, min(limit, 1000))]
        collected_at = self.collected_at()

        records = []
        for item in vulnerabilities:
            records.append(
                {
                    "source": "cisa_kev",
                    "record_type": "known_exploited_vulnerability",
                    "source_record_id": item.get("cveID"),
                    "title": item.get("vulnerabilityName") or item.get("cveID"),
                    "vendor": item.get("vendorProject"),
                    "product": item.get("product"),
                    "description": item.get("shortDescription"),
                    "date_added": item.get("dateAdded"),
                    "due_date": item.get("dueDate"),
                    "known_ransomware_use": item.get("knownRansomwareCampaignUse"),
                    "required_action": item.get("requiredAction"),
                    "cwes": item.get("cwes", []),
                    "provenance": {
                        "source_name": self.source_name,
                        "source_type": "government_vulnerability_catalog",
                        "source_url": self.catalog_url,
                        "publisher": "Cybersecurity and Infrastructure Security Agency",
                        "collected_at": collected_at.isoformat(),
                        "source_record_id": item.get("cveID"),
                        "retrieval_method": "https_json",
                        "content_hash": self.stable_hash(item),
                        "reliability_score": 0.98,
                    },
                }
            )

        return {
            "source": "cisa_kev",
            "catalog_version": payload.get("catalogVersion"),
            "date_released": payload.get("dateReleased"),
            "count": len(records),
            "records": records,
        }
