from app.services.conflict_intelligence.conflict_event_classifier import (
    ConflictEventClassifier,
)


def classify(title: str):
    return ConflictEventClassifier.classify(
        title=title,
        summary="",
    )


def test_missile_barrage():
    result = classify(
        "Russia launches massive missile barrage against Ukrainian cities"
    )
    assert result["event_type"] == "missile_strike"
    assert result["supports_escalation"] is True


def test_drone_assault():
    result = classify(
        "Ukraine attacks Russia with hundreds of drones in major aerial assault"
    )
    assert result["event_type"] == "airstrike"
    assert result["supports_escalation"] is True


def test_bombardment():
    result = classify(
        "Russia bombards Kyiv and other cities in major bombardment"
    )
    assert result["event_type"] == "airstrike"


def test_heavy_fighting():
    result = classify(
        "Heavy fighting continues along the front after offensive operations"
    )
    assert result["event_type"] == "armed_clash"


def test_general_military_activity():
    result = classify(
        "Military buildup and troop deployment reported near frontier"
    )
    assert result["event_type"] == "military_activity"


def test_peace_talks_remain_deescalatory():
    result = classify(
        "Peace talks resume through international mediation"
    )
    assert result["event_type"] == "diplomatic_engagement"
    assert result["contradicts_escalation"] is True
