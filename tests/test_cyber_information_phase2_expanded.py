import pytest

from app.cyber_information.collectors.abuseipdb import AbuseIpDbCollector
from app.cyber_information.collectors.mitre_attack import MitreAttackCollector
from app.cyber_information.collectors.stix_taxii import StixBundleAdapter
from app.cyber_information.collectors.urlhaus import UrlhausCollector


@pytest.mark.asyncio
async def test_mitre_attack_normalization(monkeypatch):
    collector = MitreAttackCollector()
    async def fake(*args, **kwargs):
        return {"type": "bundle", "objects": [{
            "type": "attack-pattern", "id": "attack-pattern--1", "name": "Synthetic Technique",
            "external_references": [{"source_name": "mitre-attack", "external_id": "T9999"}],
        }]}
    monkeypatch.setattr(collector, "get_json", fake)
    result = await collector.collect(limit=1)
    assert result["records"][0]["attack_id"] == "T9999"


@pytest.mark.asyncio
async def test_urlhaus_normalization(monkeypatch):
    collector = UrlhausCollector()
    async def fake(*args, **kwargs):
        return {"urls": [{"id": "1", "url": "http://malware.test/a", "url_status": "online", "threat": "malware_download"}]}
    monkeypatch.setattr(collector, "get_json", fake)
    result = await collector.collect_recent(limit=1)
    assert result["records"][0]["record_type"] == "malware_distribution_infrastructure"


def test_generic_stix_bundle_adapter():
    result = StixBundleAdapter().normalize_bundle(
        {"type": "bundle", "objects": [{"type": "indicator", "id": "indicator--1", "name": "Synthetic IOC"}]},
        source_name="test_feed",
    )
    assert result["count"] == 1
    assert result["records"][0]["source_record_id"] == "indicator--1"


@pytest.mark.asyncio
async def test_abuseipdb_requires_key(monkeypatch):
    monkeypatch.delenv("ABUSEIPDB_API_KEY", raising=False)
    with pytest.raises(Exception, match="ABUSEIPDB_API_KEY"):
        await AbuseIpDbCollector().check(ip_address="192.0.2.1")
