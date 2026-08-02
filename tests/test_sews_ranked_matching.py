from app.services.sews_deterministic_matcher import (
    SEWSDeterministicIndicatorMatcher,
)

def _mapping(key, name, tags):
    return {
        "indicator_key": key,
        "indicator_class": "PRECURSOR",
        "weight": 1.0,
        "rationale": f"Assess {name}.",
        "sews_indicator_definitions": {
            "indicator_key": key,
            "name": name,
            "description": f"Tracks {name}.",
            "tags": tags,
            "sector_scope": [],
        },
    }

def test_ranked_matching_caps_results():
    matcher = SEWSDeterministicIndicatorMatcher()
    evidence = {
        "title": "Tanker traffic disrupted after shipping restrictions near Strait of Hormuz",
        "raw_text": "Transit restrictions reduced tanker traffic through the Strait of Hormuz.",
    }
    mappings = [
        _mapping("IND_CHOKEPOINT_TRANSIT_RESTRICTIONS","Chokepoint Transit Restrictions",["chokepoint","transit","restrictions"]),
        _mapping("IND_TANKER_TRAFFIC_DISRUPTION","Tanker Traffic Disruption",["tanker","traffic","disruption"]),
        _mapping("IND_SHIPPING_RESTRICTIONS","Shipping Restrictions",["shipping","restrictions","transit"]),
        _mapping("IND_NAVAL_DEPLOYMENT","Naval Deployment",["naval","deployment","fleet"]),
        _mapping("IND_FOOD_SECURITY","Food Security Shock",["food","shortage","agriculture"]),
    ]
    ranked = matcher.rank_for_evidence(
        evidence=evidence,
        mappings=mappings,
        limit=3,
    )
    assert len(ranked) <= 3
    keys = {m["indicator_key"] for m, _ in ranked}
    assert "IND_FOOD_SECURITY" not in keys
    assert "IND_NAVAL_DEPLOYMENT" not in keys

def test_generic_terms_do_not_match():
    matcher = SEWSDeterministicIndicatorMatcher()
    result = matcher.score(
        evidence={
            "title":"Global security risk report",
            "raw_text":"A strategic risk and security report was published.",
        },
        indicator={
            "indicator_key":"IND_NAVAL_DEPLOYMENT",
            "name":"Naval Deployment",
            "description":"Tracks naval fleet deployment.",
            "tags":["naval","fleet","deployment"],
        },
        mapping={
            "indicator_class":"PRECURSOR",
            "rationale":"Assess naval deployment.",
        },
    )
    assert result is None
