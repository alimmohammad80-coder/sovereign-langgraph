from app.services.sews_warning_scoring_service import SEWSWarningScoringService


def test_logit_round_trip():
    for p in (0.05, 0.2, 0.5, 0.8, 0.95):
        assert abs(SEWSWarningScoringService._sigmoid(SEWSWarningScoringService._logit(p)) - p) < 1e-9


def test_bands_and_states():
    assert SEWSWarningScoringService._probability_band(.1) == "0–20%"
    assert SEWSWarningScoringService._probability_band(.9) == "80–100%"
    assert SEWSWarningScoringService._state(.1).value == "DORMANT"
    assert SEWSWarningScoringService._state(.85).value == "CRITICAL"


def test_direction():
    assert SEWSWarningScoringService._direction(.6, .5) == "DETERIORATING"
    assert SEWSWarningScoringService._direction(.4, .5) == "IMPROVING"
    assert SEWSWarningScoringService._direction(.52, .5) == "STABLE"
