from app.schemas.sews_warning_scoring import WarningState
from app.services.sews_warning_ledger_service import (
    SEWSWarningLedgerService,
)


def test_same_state_is_allowed():
    assert SEWSWarningLedgerService._allowed_transition(
        WarningState.WATCH,
        WarningState.WATCH,
        force=False,
    )


def test_single_step_escalation_is_allowed():
    assert SEWSWarningLedgerService._allowed_transition(
        WarningState.WATCH,
        WarningState.ADVISORY,
        force=False,
    )


def test_single_step_deescalation_is_allowed():
    assert SEWSWarningLedgerService._allowed_transition(
        WarningState.WARNING,
        WarningState.ADVISORY,
        force=False,
    )


def test_multi_step_transition_requires_force():
    assert not SEWSWarningLedgerService._allowed_transition(
        WarningState.DORMANT,
        WarningState.WARNING,
        force=False,
    )
    assert SEWSWarningLedgerService._allowed_transition(
        WarningState.DORMANT,
        WarningState.WARNING,
        force=True,
    )


def test_resolved_state_cannot_reopen_without_force():
    assert not SEWSWarningLedgerService._allowed_transition(
        WarningState.RESOLVED,
        WarningState.WATCH,
        force=False,
    )


def test_ledger_number_is_deterministic():
    number = SEWSWarningLedgerService._ledger_number(
        "WP-HORMUZ-CLOSURE",
        3,
    )
    assert number.endswith("HORMUZ-CLOSURE-V003")
