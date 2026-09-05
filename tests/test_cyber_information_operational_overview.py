from app.cyber_information.operational_overview import (
    _executive_judgment,
    _information_products,
    _priority_exposures,
    _priority_incidents,
)


def kev(cve: str, *, ransomware: str = "Unknown") -> dict:
    return {
        "source": "cisa_kev",
        "record_type": "known_exploited_vulnerability",
        "source_record_id": cve,
        "title": f"Exploited vulnerability {cve}",
        "description": f"Observed exploitation of {cve}",
        "vendor": "Example Vendor",
        "product": "Example Product",
        "known_ransomware_use": ransomware,
        "provenance": {
            "source_name": "CISA Known Exploited Vulnerabilities",
            "source_type": "government_vulnerability_catalog",
            "publisher": "CISA",
            "reliability_score": 0.98,
        },
    }


def gdelt(title: str, domain: str, seen: str) -> dict:
    return {
        "source": "gdelt",
        "record_type": "information_environment_observation",
        "source_record_id": f"https://{domain}/{seen}",
        "title": title,
        "url": f"https://{domain}/{seen}",
        "domain": domain,
        "language": "English",
        "source_country": "United States",
        "seen_date": seen,
        "provenance": {
            "source_name": "GDELT Project DOC 2.0",
            "source_type": "global_news_event_index",
            "publisher": domain,
            "reliability_score": 0.72,
        },
    }


def test_priority_products_surface_ransomware_and_exploitation():
    records = [kev("CVE-2026-1001", ransomware="Known"), kev("CVE-2026-1002")]
    incidents = _priority_incidents(records)
    exposures = _priority_exposures(records)
    assert incidents[0]["severity_score"] >= 88
    assert exposures[0]["known_exploited"] is True
    assert exposures[0]["exposure_score"] >= exposures[1]["exposure_score"]


def test_information_products_create_analytic_campaign_objects():
    records = [
        gdelt("Coordinated cyber attack targets national energy network", "a.test", "20260904T120000Z"),
        gdelt("Cyber attack targets national energy network amid crisis", "b.test", "20260904T121000Z"),
        gdelt("National energy network targeted in coordinated cyber attack", "c.test", "20260904T122000Z"),
    ]
    products = _information_products(records)
    assert products
    top = products[0]
    assert top["observation_count"] >= 2
    assert "energy" in top["sectors"]
    assert top["strategic_relevance_score"] > 0
    assert "coordination_score" in top


def test_executive_judgment_is_explainable():
    narratives = [{
        "label": "Energy-network cyber attack narrative",
        "strategic_relevance_score": 74.0,
        "coordination_score": 61.0,
    }]
    result = _executive_judgment([kev("CVE-2026-1001", ransomware="Known")], [], narratives)
    assert result["posture_level"] in {"Guarded", "Elevated", "High", "Critical"}
    assert result["key_drivers"]
    assert "ransomware" in " ".join(result["key_drivers"]).lower()
