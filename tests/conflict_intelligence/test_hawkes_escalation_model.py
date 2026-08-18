from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services.conflict_intelligence.hawkes_escalation_model import (
    HawkesEscalationModel,
)


def model_without_db():
    model = HawkesEscalationModel.__new__(
        HawkesEscalationModel
    )

    import json
    from app.services.conflict_intelligence.hawkes_escalation_model import (
        PARAMETERS_PATH,
        CLASSIFICATION_PATH,
    )

    model.parameters = json.loads(
        PARAMETERS_PATH.read_text()
    )

    model.classification = json.loads(
        CLASSIFICATION_PATH.read_text()
    )

    return model


def test_recent_event_stronger_than_old_event():

    model = model_without_db()

    now = datetime.now(
        timezone.utc
    )

    recent = {
        "observation_key": "RECENT",
        "observed_at": (
            now
            - timedelta(days=1)
        ).isoformat(),
        "event_type": "military_activity",
        "severity": 70,
        "confidence_grade": "high",
        "source": "test",
    }

    old = {
        **recent,
        "observation_key": "OLD",
        "observed_at": (
            now
            - timedelta(days=60)
        ).isoformat(),
    }

    a = model._event_contribution(
        recent,
        now,
    )

    b = model._event_contribution(
        old,
        now,
    )

    assert (
        a["contribution"]
        >
        b["contribution"]
    )


def test_peace_event_is_negative():

    model = model_without_db()

    now = datetime.now(
        timezone.utc
    )

    row = {
        "observation_key": "PEACE",
        "observed_at": now.isoformat(),
        "event_type": "peace_agreement",
        "severity": 80,
        "confidence_grade": "high",
        "source": "test",
    }

    result = model._event_contribution(
        row,
        now,
    )

    assert (
        result[
            "contribution"
        ]
        < 0
    )


def test_probability_bounded():

    model = model_without_db()

    probability, _ = (
        model._logistic_probability(
            state_code="S2_CRISIS",
            current_intensity=0.05,
            burst=0.2,
            event_count=2,
            severity_mean=60,
            horizon_days=30,
        )
    )

    assert 0.0 <= probability <= 1.0


def test_more_intensity_means_more_risk():

    model = model_without_db()

    low, _ = (
        model._logistic_probability(
            "S2_CRISIS",
            0.01,
            0.1,
            1,
            40,
            30,
        )
    )

    high, _ = (
        model._logistic_probability(
            "S2_CRISIS",
            0.08,
            0.5,
            5,
            70,
            30,
        )
    )

    assert high > low
