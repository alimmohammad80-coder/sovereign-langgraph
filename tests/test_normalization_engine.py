from app.normalization.normalization_engine import (
    NormalizationEngine,
)
from app.normalization.normalizers.gdelt_normalizer import (
    GDELTNormalizer,
)


def test_gdelt_record_normalization() -> None:
    engine = NormalizationEngine([GDELTNormalizer()])

    record = engine.normalize(
        "GDELT",
        {
            "source_external_id": "sews-test-001",
            "title": "Naval activity increases near Hormuz",
            "raw_text": (
                "Multiple naval units were reported operating "
                "near the Strait of Hormuz."
            ),
            "country_iso3": "IRN",
            "region_key": "MIDDLE_EAST",
            "location_name": "Strait of Hormuz",
            "actor1_name": "Iran",
            "actor1_country_code": "IRN",
            "event_type": "MILITARY_ACTIVITY",
            "direction": "INCREASING",
            "severity": 78,
            "confidence": 84,
            "source_reliability": 90,
            "published_at": "2026-07-30T15:00:00Z",
            "canonical_url": (
                "https://example.com/sews-test-001"
            ),
            "themes": [
                "Military Posture",
                "Maritime Security",
            ],
            "sectors": ["Energy", "Shipping"],
        },
    )

    assert record.source_key == "GDELT"
    assert record.record_type == "EVENT"
    assert record.event_type == "MILITARY_ACTIVITY"
    assert record.location.country_iso3 == "IRN"
    assert record.direction == "INCREASING"
    assert record.severity == 78
    assert record.confidence == 0.84
    assert record.source_reliability == 0.90
    assert len(record.entities) >= 2
