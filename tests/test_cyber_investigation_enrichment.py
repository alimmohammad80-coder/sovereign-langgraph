from app.cyber_information.investigation_enrichment import enrich_investigation


def _mitre_records():
    return [
        {
            "source_record_id": "attack-pattern--public-facing",
            "attack_id": "T1190",
            "name": "Exploit Public-Facing Application",
            "kill_chain_phases": [{"phase_name": "initial-access"}],
            "raw_stix": {"type": "attack-pattern", "id": "attack-pattern--public-facing"},
        },
        {
            "source_record_id": "intrusion-set--example",
            "name": "Example Threat Group",
            "raw_stix": {"type": "intrusion-set", "id": "intrusion-set--example"},
        },
        {
            "source_record_id": "relationship--1",
            "raw_stix": {
                "type": "relationship",
                "relationship_type": "uses",
                "source_ref": "intrusion-set--example",
                "target_ref": "attack-pattern--public-facing",
            },
        },
    ]


def test_investigation_maps_public_facing_technique_and_keeps_hypothesis_caveat():
    record = {
        "record_type": "known_exploited_vulnerability",
        "title": "Remote access gateway vulnerability",
        "date_added": "2026-09-04",
        "provenance": {"collected_at": "2026-09-04T20:00:00Z"},
    }
    incident = {
        "title": "Remote access gateway vulnerability",
        "summary": "An internet-facing gateway is actively exploited.",
        "indicators": [],
        "countries": [],
    }
    threat_context = {
        "asset_role": "internet-facing remote-access infrastructure",
        "why_targeted": "The appliance is exposed to the internet.",
        "likely_attacker_objectives": ["gain initial access"],
    }

    result = enrich_investigation(
        record=record,
        incident=incident,
        threat_context=threat_context,
        mitre_records=_mitre_records(),
    )

    assert result["attack_techniques"][0]["attack_id"] == "T1190"
    assert result["attack_techniques"][0]["name"] == "Exploit Public-Facing Application"
    assert result["actor_hypotheses"][0]["name"] == "Example Threat Group"
    assert result["actor_hypotheses"][0]["hypothesis_strength"] == "low"
    assert "not attribution" in result["actor_hypotheses"][0]["analytic_caveat"].lower()
    assert "Victim or exploitation geography unresolved" in result["intelligence_gaps"]


def test_indicator_relationships_and_timeline_are_observed_evidence():
    record = {
        "record_type": "malware_distribution_infrastructure",
        "published": "2026-09-04T18:00:00Z",
        "provenance": {"collected_at": "2026-09-04T19:00:00Z"},
    }
    incident = {
        "title": "Malware infrastructure",
        "summary": "Observed malicious host.",
        "indicators": [{"type": "ip", "value": "192.0.2.10"}],
        "countries": ["USA"],
    }
    result = enrich_investigation(
        record=record,
        incident=incident,
        threat_context={},
        mitre_records=[],
    )

    assert result["indicator_relationships"][0]["evidence_status"] == "observed"
    assert result["indicator_relationships"][0]["value"] == "192.0.2.10"
    assert [event["event_type"] for event in result["evidence_timeline"]] == ["source_publication", "platform_collection"]
