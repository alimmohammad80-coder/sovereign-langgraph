from app.schemas.sews import AssessmentRequest
from app.services.sews_engine import assess


def test_contra_evidence_reduces_probability() -> None:
    base = {
        "problem_key": "WP-TWN-BLOCKADE",
        "base_rate": 0.08,
        "current_state": "WATCH",
        "severity_score": 92,
        "model_agreement": 0.8,
    }

    supporting = AssessmentRequest(
        **base,
        indicators=[
            {
                "indicator_key": "IND-001",
                "class": "PRECURSOR",
                "status": "ACTIVE",
                "weight": 1.0,
                "baseline_z": 2.5,
                "age_days": 0,
                "source_domains": 2,
            }
        ],
    )
    with_contra = AssessmentRequest(
        **base,
        indicators=[
            {
                "indicator_key": "IND-001",
                "class": "PRECURSOR",
                "status": "ACTIVE",
                "weight": 1.0,
                "baseline_z": 2.5,
                "age_days": 0,
                "source_domains": 2,
            },
            {
                "indicator_key": "IND-004",
                "class": "CONTRA",
                "status": "CONTRADICTING",
                "weight": 0.8,
                "baseline_z": 2.0,
                "age_days": 0,
                "source_domains": 2,
            },
        ],
    )

    assert assess(with_contra).probability < assess(supporting).probability


def test_dark_feed_reduces_confidence() -> None:
    payload = AssessmentRequest(
        problem_key="WP-TWN-BLOCKADE",
        base_rate=0.08,
        current_state="WATCH",
        severity_score=92,
        model_agreement=0.8,
        indicators=[
            {
                "indicator_key": "IND-001",
                "class": "PRECURSOR",
                "status": "DARK",
                "weight": 1.0,
                "reporting": False,
                "source_domains": 0,
            },
            {
                "indicator_key": "IND-002",
                "class": "ACCELERANT",
                "status": "ACTIVE",
                "weight": 1.0,
                "source_domains": 2,
            },
        ],
    )

    result = assess(payload)
    assert result.confidence_breakdown.collection_integrity == 0.5
    assert result.confidence_breakdown.indicator_coverage == 0.5


def test_output_uses_probability_band() -> None:
    payload = AssessmentRequest(
        problem_key="WP-TWN-BLOCKADE",
        base_rate=0.08,
        current_state="DORMANT",
        severity_score=92,
        indicators=[],
    )
    result = assess(payload)
    assert result.probability_band == "0–20%"
