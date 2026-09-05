from app.cyber_information.threat_context import build_threat_context


def test_sonicwall_context_is_useful_but_unattributed():
    record = {
        "source": "cisa_kev",
        "record_type": "known_exploited_vulnerability",
        "source_record_id": "CVE-2026-15409",
        "vendor": "SonicWall",
        "product": "SMA1000 Appliances",
        "title": "SonicWall SMA1000 Appliances Server-Side Request Forgery Vulnerability",
        "description": "Remote unauthenticated attacker may cause the appliance to make unintended requests.",
        "known_ransomware_use": "Unknown",
    }
    context = build_threat_context(record)
    assert context["attribution_status"] == "unattributed"
    assert context["associated_actors"] == []
    assert "remote-access" in context["asset_role"]
    assert "gain initial access" in context["likely_attacker_objectives"]
    assert "No specific threat actor" in context["attribution_summary"]
    assert "Observed exploitation" in context["exploitation_summary"]


def test_ransomware_context_names_actor_class_not_group():
    record = {
        "record_type": "known_exploited_vulnerability",
        "vendor": "Example",
        "product": "Gateway",
        "title": "Example vulnerability",
        "known_ransomware_use": "Known",
    }
    context = build_threat_context(record)
    assert context["attribution_status"] == "actor_unspecified_ransomware_use"
    assert context["associated_actors"][0]["name"] == "Ransomware operators"
    assert "specific group" in context["associated_actors"][0]["relationship"]


def test_source_reported_actor_is_labeled_as_source_reported():
    context = build_threat_context({
        "record_type": "known_exploited_vulnerability",
        "title": "Synthetic test",
        "threat_actor": "Example Actor",
    })
    assert context["attribution_status"] == "source_reported"
    assert context["associated_actors"][0]["name"] == "Example Actor"
    assert context["attribution_confidence"] == "moderate"
