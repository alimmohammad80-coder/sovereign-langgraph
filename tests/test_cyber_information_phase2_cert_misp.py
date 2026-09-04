import pytest

from app.cyber_information.collectors.cert_feeds import cert_feed_registry
from app.cyber_information.collectors.misp import MispCollector


def test_cert_registry_contains_official_feeds():
    registry = cert_feed_registry()
    assert "uk_ncsc_threat_reports" in registry
    assert "canada_cyber_alerts" in registry
    assert registry["uk_ncsc_threat_reports"]["country_iso3"] == "GBR"
    assert registry["canada_cyber_alerts"]["country_iso3"] == "CAN"


def test_misp_event_normalization():
    event = {
        "id": "42",
        "uuid": "11111111-2222-3333-4444-555555555555",
        "info": "Synthetic MISP event",
        "Attribute": [{
            "uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "type": "ip-dst",
            "category": "Network activity",
            "value": "192.0.2.10",
            "to_ids": True,
            "comment": "Synthetic test IOC",
            "timestamp": "1788552000",
        }],
    }
    record = MispCollector().normalize_event(event, source_url="https://misp.example.test")
    assert record["record_type"] == "misp_event"
    assert record["source_record_id"] == event["uuid"]
    assert record["attributes"][0]["type"] == "ip-dst"
    assert record["provenance"]["content_hash"]


@pytest.mark.asyncio
async def test_misp_collect_uses_post(monkeypatch):
    collector = MispCollector()
    captured = {}

    async def fake_post_json(url, *, payload=None, headers=None):
        captured["url"] = url
        captured["payload"] = payload
        captured["headers"] = headers
        return {"response": [{"Event": {"id": "1", "uuid": "event-uuid", "info": "Synthetic"}}]}

    monkeypatch.setenv("MISP_API_KEY", "test-key")
    monkeypatch.setattr(collector, "post_json", fake_post_json)
    result = await collector.collect_events(base_url="https://misp.example.test", limit=1)
    assert captured["url"].endswith("/events/restSearch")
    assert captured["payload"]["returnFormat"] == "json"
    assert captured["headers"]["Authorization"] == "test-key"
    assert result["count"] == 1
