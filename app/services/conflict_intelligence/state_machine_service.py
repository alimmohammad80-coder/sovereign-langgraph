from __future__ import annotations

from app.schemas.conflict_intelligence.common import (
    ConflictState,
    SeverityTier,
    STATE_TO_SEVERITY,
)


ALLOWED_TRANSITIONS: dict[ConflictState, set[ConflictState]] = {
    ConflictState.S0_STABLE: {ConflictState.S1_TENSION},
    ConflictState.S1_TENSION: {
        ConflictState.S0_STABLE,
        ConflictState.S2_CRISIS,
    },
    ConflictState.S2_CRISIS: {
        ConflictState.S1_TENSION,
        ConflictState.S3_LIMITED_CONFLICT,
        ConflictState.S5_FROZEN,
    },
    ConflictState.S3_LIMITED_CONFLICT: {
        ConflictState.S2_CRISIS,
        ConflictState.S4_WAR,
        ConflictState.S5_FROZEN,
    },
    ConflictState.S4_WAR: {
        ConflictState.S3_LIMITED_CONFLICT,
        ConflictState.S5_FROZEN,
    },
    ConflictState.S5_FROZEN: {
        ConflictState.S1_TENSION,
        ConflictState.S2_CRISIS,
        ConflictState.S3_LIMITED_CONFLICT,
    },
}


class InvalidStateTransition(ValueError):
    pass


def validate_transition(current: ConflictState, target: ConflictState) -> bool:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidStateTransition(f"Unsupported transition: {current.value} -> {target.value}")
    return True


def severity_for_state(state: ConflictState) -> SeverityTier:
    return STATE_TO_SEVERITY[state]
