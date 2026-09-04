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
        "Attribute": [
            {
                "uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "type": "ip-dst",
                "category": "Network activity",
                "value": "192.0.2.10",
                "to_ids": True,
                "comment": "Synthetic test IOC",
                "timestamp": "1788552000",
            }
        ],
    }
    record = MispCollector().normalize_event(event, source_url="https://misp.example.test")
    assert record["record_type"] == "misp_event"
    assert record["source_record_id"] == event["uuid"]
    assert record["attributes"][0]["type"] == "ip-dst"
    assert record["provenance"]["content_hash"]
