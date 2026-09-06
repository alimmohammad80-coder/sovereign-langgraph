import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from services.financial_corporate.calibrated_hazards import CalibratedCorporateHazardService
from services.financial_corporate.evidence_calibration import EvidenceCalibratedCorporateHazardService


class _FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class CalibratedCorporateHazardTests(unittest.TestCase):
    def setUp(self):
        self.service = CalibratedCorporateHazardService()
        self.entity = {
            "entity_id": "corp_nvidia",
            "common_name": "NVIDIA",
            "legal_name": "NVIDIA Corporation",
        }

    def test_old_cve_modified_recently_does_not_count_as_current_pressure(self):
        now = datetime.now(timezone.utc)
        payload = {
            "vulnerabilities": [
                {
                    "cve": {
                        "id": "CVE-2006-0001",
                        "published": "2006-10-18T04:06:00.000",
                        "lastModified": (now - timedelta(days=2)).isoformat().replace("+00:00", "Z"),
                        "descriptions": [{"lang": "en", "value": "NVIDIA legacy driver issue"}],
                        "metrics": {},
                    }
                }
            ]
        }
        with patch("services.financial_corporate.calibrated_hazards.urllib.request.urlopen", return_value=_FakeResponse(payload)):
            result = self.service.nvd_company_pressure(self.entity)
        self.assertEqual(result["status"], "screened_no_recent_published_match")
        self.assertIsNone(result["score"])
        self.assertEqual(result["date_basis"], "published")

    def test_recent_published_cve_counts_as_current_pressure(self):
        now = datetime.now(timezone.utc)
        payload = {
            "vulnerabilities": [
                {
                    "cve": {
                        "id": "CVE-2026-9999",
                        "published": (now - timedelta(days=5)).isoformat().replace("+00:00", "Z"),
                        "lastModified": (now - timedelta(days=1)).isoformat().replace("+00:00", "Z"),
                        "descriptions": [{"lang": "en", "value": "NVIDIA GPU driver remote code execution vulnerability"}],
                        "metrics": {
                            "cvssMetricV31": [
                                {"cvssData": {"baseScore": 9.1}}
                            ]
                        },
                    }
                }
            ]
        }
        with patch("services.financial_corporate.calibrated_hazards.urllib.request.urlopen", return_value=_FakeResponse(payload)):
            result = self.service.nvd_company_pressure(self.entity)
        self.assertEqual(result["status"], "observed")
        self.assertEqual(result["matched_count"], 1)
        self.assertGreater(result["score"], 0)
        self.assertEqual(result["date_basis"], "published")

    def test_victim_attribution_rejects_supplier_incident_as_enterprise_incident(self):
        recent = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%a, %d %b %Y %H:%M:%S GMT")
        items = [
            {
                "title": "NVIDIA confirms data breach affecting cloud users",
                "published": recent,
                "source": "BleepingComputer",
            },
            {
                "title": "Foxconn confirms ransomware attack involving files for NVIDIA and Apple",
                "published": recent,
                "source": "The Register",
            },
        ]
        contextual = self.service._weighted_media_pressure(entity=self.entity, items=items, cyber=True)
        hardened = EvidenceCalibratedCorporateHazardService.direct_enterprise_incident_pressure(
            self.entity,
            {"matched_items": contextual["matched"]},
        )
        self.assertEqual(hardened["status"], "observed")
        self.assertEqual(hardened["matched_count"], 1)
        self.assertIn("NVIDIA confirms data breach", hardened["matched_items"][0]["title"])
        rejected_titles = [item["title"] for item in hardened.get("rejected_co_mentions") or []]
        self.assertTrue(any("Foxconn confirms ransomware" in title for title in rejected_titles))


if __name__ == "__main__":
    unittest.main()
