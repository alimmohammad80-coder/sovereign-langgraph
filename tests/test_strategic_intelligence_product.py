from app.services.strategic_intelligence_product_service import (
    StrategicIntelligenceProductService,
)


def test_sentence_count():
    text = "Sentence one. Sentence two! Sentence three?"
    assert StrategicIntelligenceProductService._sentence_count(text) == 3


def test_word_count():
    text = "This is a five word sentence."
    assert StrategicIntelligenceProductService._word_count(text) == 6


def test_product_key_is_deterministic():
    from uuid import UUID

    assessment_id = UUID("11111111-1111-1111-1111-111111111111")
    first = StrategicIntelligenceProductService._product_key(
        "WP-HORMUZ-CLOSURE",
        assessment_id,
        "SEWS_WARNING",
    )
    second = StrategicIntelligenceProductService._product_key(
        "WP-HORMUZ-CLOSURE",
        assessment_id,
        "SEWS_WARNING",
    )
    assert first == second
    assert first.startswith("SIP-WP-HORMUZ-CLOSURE-")


def test_indicator_split():
    assessment = {
        "indicator_snapshot": [
            {
                "indicator_key": "A",
                "weighted_contribution": 0.4,
                "confidence": 80,
            },
            {
                "indicator_key": "B",
                "weighted_contribution": -0.3,
                "confidence": 75,
            },
        ]
    }

    drivers, contra = (
        StrategicIntelligenceProductService._indicator_drivers(
            assessment
        )
    )

    assert drivers[0]["indicator_key"] == "A"
    assert contra[0]["indicator_key"] == "B"
