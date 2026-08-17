import pytest

from app.schemas.conflict_intelligence.common import ConflictState, SeverityTier
from app.services.conflict_intelligence.state_machine_service import (
    InvalidStateTransition,
    severity_for_state,
    validate_transition,
)


def test_valid_transition():
    assert validate_transition(ConflictState.S1_TENSION, ConflictState.S2_CRISIS)


def test_invalid_transition():
    with pytest.raises(InvalidStateTransition):
        validate_transition(ConflictState.S0_STABLE, ConflictState.S4_WAR)


def test_state_to_severity():
    assert severity_for_state(ConflictState.S4_WAR) == SeverityTier.CRITICAL
    assert severity_for_state(ConflictState.S5_FROZEN) == SeverityTier.GUARDED
