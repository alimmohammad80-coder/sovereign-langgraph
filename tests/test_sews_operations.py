from app.services.sews_deterministic_matcher import SEWSDeterministicIndicatorMatcher
from app.services.sews_material_change_service import SEWSMaterialChangeService

def test_deterministic_matcher():
    result = SEWSDeterministicIndicatorMatcher().match(
        evidence={"title":"Naval deployment increases near Taiwan","raw_text":"Naval readiness drills expanded."},
        indicator={
            "indicator_key":"IND_NAVAL_DEPLOYMENT_PRECURSOR",
            "name":"Naval Deployment",
            "description":"Tracks naval force posture and readiness.",
            "primary_domain":"Conflict and Military",
            "tags":["naval","deployment","readiness"],
        },
        mapping={"indicator_class":"PRECURSOR","rationale":"Assess naval deployment and readiness."},
    )
    assert result is not None
    assert result.polarity == "SUPPORTING"

def test_material_change():
    result = SEWSMaterialChangeService().evaluate(
        previous={"probability":0.40,"confidence_score":70,"recommended_state":"WATCH","direction":"STABLE"},
        current={"probability":0.48,"confidence_score":77,"recommended_state":"ADVISORY","direction":"RISING"},
    )
    assert result.material_change is True
