from app.cyber_information.cyber_engine import CyberIntelligenceEngine
from app.cyber_information.graph_builder import CyberGraphBuilder


engine = CyberIntelligenceEngine()


def _kev_record():
    return {
        "source": "cisa_kev",
        "record_type": "known_exploited_vulnerability",
        "source_record_id": "CVE-2026-12345",
        "title": "Synthetic gateway vulnerability",
        "description": "CVE-2026-12345 is being exploited in the wild.",
        "vendor": "ExampleVendor",
        "product": "Gateway",
        "known_ransomware_use": "Known",
        "provenance": {
            "source_name": "CISA Known Exploited Vulnerabilities",
            "source_type": "government_vulnerability_catalog",
            "source_url": "https://example.test/kev",
            "publisher": "CISA",
            "retrieval_method": "https_json",
            "content_hash": "abc123",
            "reliability_score": 0.98,
        },
    }


def test_incident_normalization_from_kev():
    incident = engine.incident_from_record(_kev_record())
    assert incident.incident_type.value == "exploitation"
    assert incident.severity_score >= 88
    assert incident.cves == ["CVE-2026-12345"]
    assert incident.confidence.score > 0.6


def test_vulnerability_exposure_is_explainable():
    exposure = engine.vulnerability_exposure(_kev_record(), target_criticality_score=90)
    assert exposure.known_exploited is True
    assert exposure.known_ransomware_use is True
    assert exposure.exposure_level.value in {"high", "critical"}
    assert exposure.exposure_score >= 80
    assert exposure.rationale


def test_urlhaus_becomes_malware_incident():
    record = {
        "source": "urlhaus",
        "record_type": "malware_distribution_infrastructure",
        "source_record_id": "1",
        "url": "http://malware.example/payload",
        "url_status": "online",
        "threat": "malware_download",
        "provenance": {
            "source_name": "URLhaus",
            "source_type": "community_malware_infrastructure_feed",
            "source_url": "https://urlhaus.abuse.ch/",
            "reliability_score": 0.86,
        },
    }
    incident = engine.incident_from_record(record)
    assert incident.incident_type.value == "malware_activity"
    assert incident.indicators[0]["type"] == "url"
    assert incident.severity_score >= 72


def test_actor_campaign_link_from_stix_relationship():
    record = {
        "source": "mitre_attack",
        "record_type": "relationship",
        "raw_stix": {
            "type": "relationship",
            "source_ref": "intrusion-set--actor-1",
            "target_ref": "campaign--campaign-1",
            "relationship_type": "uses",
        },
        "provenance": {
            "source_name": "MITRE ATT&CK",
            "source_type": "stix_2_1_knowledge_base",
            "reliability_score": 0.98,
        },
    }
    link = engine.actor_campaign_link(record)
    assert link is not None
    assert link.actor_name == "intrusion-set--actor-1"
    assert link.campaign_name == "campaign--campaign-1"
    assert link.relationship == "uses"


def test_infrastructure_target_profile():
    incident = engine.incident_from_record(_kev_record())
    incident.sectors = ["energy"]
    profile = engine.infrastructure_target_profile(
        name="Synthetic Energy Operator",
        sector="energy",
        country_iso3="USA",
        criticality_score=95,
        incidents=[incident],
    )
    assert profile.observed_incident_count == 1
    assert profile.targeting_score > 60
    assert "CVE-2026-12345" in profile.vulnerability_ids


def test_graph_builder_creates_vulnerability_relationship():
    incident = engine.incident_from_record(_kev_record())
    graph = CyberGraphBuilder().incident_graph(incident)
    assert len(graph["entities"]) >= 2
    assert any(r["relationship_type"] == "exploits" for r in graph["relationships"])
