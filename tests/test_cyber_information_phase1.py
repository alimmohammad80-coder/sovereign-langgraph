from fastapi.testclient import TestClient

from app.cyber_information.confidence import assess_confidence
from app.main import app


client = TestClient(app)


def test_confidence_is_deterministic_and_bounded():
    result = assess_confidence(
        evidence_quality=0.9,
        source_diversity=0.8,
        corroboration=0.85,
        analytic_uncertainty=0.2,
        rationale="test",
    )
    assert result.score == 0.85
    assert result.level.value == "high"


def test_ontology_endpoint():
    response = client.get("/api/cyber-information/ontology")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["version"] == "cyber-info-ontology-v1"
    assert "threat_actor" in data["entity_types"]
    assert "attributed_to" in data["relationship_types"]


def test_event_contract_validation():
    payload = {
        "domain": "hybrid",
        "event_type": "coordinated_activity",
        "title": "Example hybrid activity",
        "summary": "Synthetic Phase 1 contract validation event.",
        "evidence_status": "assessed",
        "countries": ["TWN"],
        "sectors": ["telecommunications"],
        "severity_score": 78,
        "confidence": {
            "score": 0.8,
            "level": "high",
            "evidence_quality": 0.85,
            "source_diversity": 0.75,
            "corroboration": 0.85,
            "analytic_uncertainty": 0.2,
            "rationale": "Synthetic test data"
        },
        "destinations": ["strategic_early_warning", "country_intelligence"]
    }
    response = client.post("/api/cyber-information/events/validate", json=payload)
    assert response.status_code == 200
    assert response.json()["valid"] is True
    assert response.json()["schema_version"] == "cyber-info-event-v1"
