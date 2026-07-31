from app.schemas.sews_ai_review import ReviewDisposition
from app.services.sews_ai_review_service import (
    SEWSAIReviewService,
)


def test_disposition_thresholds():
    assert (
        SEWSAIReviewService._disposition(0.03)
        == ReviewDisposition.AGREE
    )
    assert (
        SEWSAIReviewService._disposition(0.08)
        == ReviewDisposition.MINOR_DISAGREEMENT
    )
    assert (
        SEWSAIReviewService._disposition(0.15)
        == ReviewDisposition.MAJOR_DISAGREEMENT
    )
    assert (
        SEWSAIReviewService._disposition(0.25)
        == ReviewDisposition.CRITICAL_DIVERGENCE
    )


def test_agreement_score():
    assert SEWSAIReviewService._agreement_score(0.04) == 0.96
    assert SEWSAIReviewService._agreement_score(-0.20) == 0.8


def test_review_payload_validation():
    payload = SEWSAIReviewService._validate_review(
        {
            "suggested_probability": 0.71,
            "suggested_confidence": 0.82,
            "recommended_state": "warning",
            "key_drivers": ["Driver 1"],
            "contrary_evidence": ["Contra 1"],
            "confidence_rationale": "Rationale",
            "monitoring_priorities": ["Priority 1"],
            "historical_analogs": [],
            "narrative": "Narrative",
        }
    )

    assert payload["recommended_state"] == "WARNING"
    assert payload["suggested_probability"] == 0.71
