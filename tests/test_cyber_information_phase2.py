import pytest

from app.cyber_information.collectors.cisa_kev import CisaKevCollector
from app.cyber_information.collectors.gdelt import GdeltCollector
from app.cyber_information.collectors.nvd import NvdCollector


@pytest.mark.asyncio
async def test_cisa_kev_normalization(monkeypatch):
    collector = CisaKevCollector()

    async def fake_get_json(*args, **kwargs):
        return {
            "catalogVersion": "test",
            "dateReleased": "2026-09-04T00:00:00Z",
            "vulnerabilities": [{
                "cveID": "CVE-2026-0001",
                "vendorProject": "Example",
                "product": "Gateway",
                "vulnerabilityName": "Example flaw",
                "shortDescription": "Synthetic test record",
                "dateAdded": "2026-09-04",
                "dueDate": "2026-09-25",
                "knownRansomwareCampaignUse": "Unknown",
                "requiredAction": "Apply mitigations",
                "cwes": ["CWE-79"],
            }],
        }

    monkeypatch.setattr(collector, "get_json", fake_get_json)
    result = await collector.collect(limit=1)
    assert result["count"] == 1
    assert result["records"][0]["source_record_id"] == "CVE-2026-0001"
    assert result["records"][0]["provenance"]["content_hash"]


@pytest.mark.asyncio
async def test_nvd_normalization(monkeypatch):
    collector = NvdCollector()

    async def fake_get_json(*args, **kwargs):
        return {"vulnerabilities": [{"cve": {
            "id": "CVE-2026-0002",
            "published": "2026-09-04T00:00:00.000",
            "lastModified": "2026-09-04T01:00:00.000",
            "vulnStatus": "Analyzed",
            "descriptions": [{"lang": "en", "value": "Synthetic NVD record"}],
            "weaknesses": [], "references": [], "metrics": {}
        }}]}

    monkeypatch.setattr(collector, "get_json", fake_get_json)
    result = await collector.collect_recent(hours=24, limit=1)
    assert result["count"] == 1
    assert result["records"][0]["description"] == "Synthetic NVD record"


@pytest.mark.asyncio
async def test_gdelt_normalization(monkeypatch):
    collector = GdeltCollector()

    async def fake_get_json(*args, **kwargs):
        return {"articles": [{
            "url": "https://example.test/article",
            "title": "Synthetic information environment signal",
            "domain": "example.test",
            "language": "English",
            "sourcecountry": "United States",
            "seendate": "20260904T120000Z",
        }]}

    monkeypatch.setattr(collector, "get_json", fake_get_json)
    result = await collector.search(query="synthetic", max_records=1)
    assert result["count"] == 1
    assert result["records"][0]["record_type"] == "information_environment_observation"
