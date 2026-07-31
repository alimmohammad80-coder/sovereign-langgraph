from app.intelligence_core.observations.engine import (
    ObservationEngine,
)
from app.intelligence_core.observations.schemas import (
    MaterialityLevel,
    ObservationDirection,
)
from app.normalization.normalization_engine import (
    NormalizationEngine,
)
from app.normalization.normalizers.gdelt_normalizer import (
    GDELTNormalizer,
)


def test_canonical_record_becomes_observation() -> None:
    normalizer = NormalizationEngine([GDELTNormalizer()])
    observation_engine = ObservationEngine()

    record = normalizer.normalize(
        "GDELT",
        {
            "source_external_id": "hormuz-test-001",
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
            "severity": 82,
            "confidence": 0.91,
            "source_reliability": 0.90,
            "themes": [
                "Military Posture",
                "Maritime Security",
            ],
            "sectors": [
                "Energy",
                "Shipping",
            ],
            "metadata": {
                "novelty": 0.80,
            },
        },
    )

    observation = observation_engine.create_observation(record)

    indicator_keys = {
        impact.indicator_key
        for impact in observation.indicator_impacts
    }

    assert observation.observation_key.startswith("OBS-GDELT-")
    assert observation.country_iso3 == "IRN"
    assert observation.direction == ObservationDirection.INCREASING
    assert observation.materiality_score >= 60
    assert observation.materiality_level in {
        MaterialityLevel.HIGH,
        MaterialityLevel.CRITICAL,
    }
    assert observation.is_material is True

    assert "MILITARY_POSTURE" in indicator_keys
    assert "MARITIME_SECURITY" in indicator_keys
    assert "ENERGY_SECURITY" in indicator_keys
    assert "CONFLICT_ESCALATION" in indicator_keys


def test_low_significance_record_is_not_material() -> None:
    normalizer = NormalizationEngine([GDELTNormalizer()])
    observation_engine = ObservationEngine()

    record = normalizer.normalize(
        "GDELT",
        {
            "source_external_id": "low-test-001",
            "title": "Routine activity reported",
            "raw_text": "Routine activity continued without change.",
            "country_iso3": "IRN",
            "event_type": "GENERAL_EVENT",
            "direction": "STABLE",
            "severity": 10,
            "confidence": 0.45,
            "source_reliability": 0.50,
            "metadata": {
                "novelty": 0.10,
            },
        },
    )

    observation = observation_engine.create_observation(record)

    assert observation.is_material is False
    assert observation.materiality_level == MaterialityLevel.LOW
