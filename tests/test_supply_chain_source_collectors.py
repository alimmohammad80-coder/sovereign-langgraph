from app.ingestion.supply_chain.models import SupplyChainEvidence
from app.ingestion.supply_chain.orchestrator import (
    SupplyChainIngestionOrchestrator,
)


def test_evidence_hash_is_stable():
    evidence = SupplyChainEvidence(
        source="USGS",
        source_record_id="event-1",
        evidence_type="event",
        title="Magnitude 6 earthquake near Port of Test",
        published_at="2026-09-04T00:00:00+00:00",
    )

    assert evidence.content_hash() == evidence.content_hash()


def test_only_matched_events_are_promoted():
    unmatched = SupplyChainEvidence(
        source="GDELT",
        source_record_id="article-1",
        evidence_type="event",
        title="Generic logistics article",
        url="https://example.test/article-1",
    )
    matched = SupplyChainEvidence(
        source="GDELT",
        source_record_id="article-2",
        evidence_type="event",
        title="TSMC logistics disruption",
        url="https://example.test/article-2",
        matched_company="TSMC",
    )

    assert unmatched.to_live_event_row() is None
    assert matched.to_live_event_row()["matched_company"] == "TSMC"


def test_registry_matching_uses_names_and_aliases():
    orchestrator = object.__new__(SupplyChainIngestionOrchestrator)
    records = [
        SupplyChainEvidence(
            source="GDELT",
            source_record_id="article-3",
            evidence_type="event",
            title=(
                "Taiwan Semiconductor Manufacturing shipment delays "
                "reported at Kaohsiung"
            ),
        ).to_storage_row()
    ]
    registry = {
        "companies": [{"company_name": "TSMC"}],
        "ports": [
            {
                "port_name": "Port of Kaohsiung",
                "latitude": 22.6163,
                "longitude": 120.2880,
            }
        ],
        "chokepoints": [],
        "commodities": [],
        "corridors": [],
    }

    matched = orchestrator._match_entities(records, registry)

    assert matched[0]["matched_company"] == "TSMC"
    assert matched[0]["matched_port"] == "Port of Kaohsiung"


def test_earthquake_coordinates_match_nearby_port():
    orchestrator = object.__new__(SupplyChainIngestionOrchestrator)
    record = SupplyChainEvidence(
        source="USGS",
        source_record_id="quake-1",
        evidence_type="event",
        title="Offshore earthquake",
        raw_payload={
            "geometry": {
                "type": "Point",
                "coordinates": [120.30, 22.62, 10],
            }
        },
    ).to_storage_row()
    registry = {
        "companies": [],
        "ports": [
            {
                "port_name": "Port of Kaohsiung",
                "latitude": 22.6163,
                "longitude": 120.2880,
            }
        ],
        "chokepoints": [],
        "commodities": [],
        "corridors": [],
    }

    matched = orchestrator._match_entities([record], registry)

    assert matched[0]["matched_port"] == "Port of Kaohsiung"
    assert matched[0]["raw_payload"]["distance_to_port_km"] < 5
