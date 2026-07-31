from app.services.sews_indicator_state_service import (
    SEWSIndicatorStateService,
)


def test_trend_rising():
    assert SEWSIndicatorStateService._trend(0.70, 0.60) == "RISING"


def test_trend_falling():
    assert SEWSIndicatorStateService._trend(0.40, 0.55) == "FALLING"


def test_trend_stable():
    assert SEWSIndicatorStateService._trend(0.61, 0.60) == "STABLE"


def test_confidence_is_bounded():
    result = SEWSIndicatorStateService._confidence(
        evidence_count=1000,
        source_count=100,
        reliability=100,
        freshness=100,
        contradiction_ratio=0,
    )
    assert result == 100.0


def test_confidence_penalizes_contradiction():
    clean = SEWSIndicatorStateService._confidence(
        evidence_count=5,
        source_count=3,
        reliability=80,
        freshness=90,
        contradiction_ratio=0,
    )
    contradicted = SEWSIndicatorStateService._confidence(
        evidence_count=5,
        source_count=3,
        reliability=80,
        freshness=90,
        contradiction_ratio=0.8,
    )
    assert contradicted < clean
