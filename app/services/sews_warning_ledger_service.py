from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from supabase import Client

from app.schemas.sews_warning_ledger import (
    StateTransitionRequest,
    StateTransitionResponse,
    WarningLedgerCreateRequest,
    WarningLedgerResponse,
)
from app.schemas.sews_warning_scoring import WarningState


class SEWSWarningLedgerError(RuntimeError):
    pass


STATE_ORDER = {
    WarningState.DORMANT: 0,
    WarningState.WATCH: 1,
    WarningState.ADVISORY: 2,
    WarningState.WARNING: 3,
    WarningState.CRITICAL: 4,
    WarningState.RESOLVED: 5,
    WarningState.FALSIFIED: 5,
}


class SEWSWarningLedgerService:
    def __init__(self, db: Client):
        self.db = db

    def _problem(self, problem_key: str) -> dict[str, Any]:
        result = (
            self.db.table("sews_warning_problems")
            .select(
                "id,problem_key,title,hypothesis,horizon_days,state,"
                "severity_score,version,transition_rules,active"
            )
            .eq("problem_key", problem_key)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise SEWSWarningLedgerError(
                f"Unknown warning problem: {problem_key}"
            )
        return result.data[0]

    def _assessment(
        self,
        *,
        assessment_id: UUID,
        warning_problem_id: str,
    ) -> dict[str, Any]:
        result = (
            self.db.table("sews_assessments")
            .select("*")
            .eq("id", str(assessment_id))
            .eq("warning_problem_id", warning_problem_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise SEWSWarningLedgerError(
                "Assessment was not found for this warning problem."
            )
        return result.data[0]

    @staticmethod
    def _allowed_transition(
        from_state: WarningState,
        to_state: WarningState,
        *,
        force: bool,
    ) -> bool:
        if force:
            return True
        if from_state == to_state:
            return True
        if from_state in {WarningState.RESOLVED, WarningState.FALSIFIED}:
            return False
        if to_state in {WarningState.RESOLVED, WarningState.FALSIFIED}:
            return True

        # Normal automated movement is limited to one ladder step in either
        # direction. Larger jumps require explicit analyst/system force.
        return abs(STATE_ORDER[to_state] - STATE_ORDER[from_state]) <= 1

    def transition(
        self,
        problem_key: str,
        request: StateTransitionRequest,
    ) -> StateTransitionResponse:
        problem = self._problem(problem_key)
        assessment = self._assessment(
            assessment_id=request.assessment_id,
            warning_problem_id=problem["id"],
        )

        from_state = WarningState(problem["state"])
        to_state = WarningState(assessment["recommended_state"])

        if not self._allowed_transition(
            from_state,
            to_state,
            force=request.force,
        ):
            raise SEWSWarningLedgerError(
                f"Transition {from_state.value} → {to_state.value} "
                "exceeds one ladder step. Use force=true only after "
                "explicit adjudication."
            )

        if from_state == to_state:
            return StateTransitionResponse(
                problem_key=problem_key,
                warning_problem_id=problem["id"],
                assessment_id=request.assessment_id,
                from_state=from_state,
                to_state=to_state,
                transitioned=False,
                reason=request.reason,
            )

        now = datetime.now(timezone.utc)
        transition_row = {
            "warning_problem_id": problem["id"],
            "from_state": from_state.value,
            "to_state": to_state.value,
            "assessment_id": str(request.assessment_id),
            "reason": request.reason,
            "actor_type": request.actor_type,
            "actor_id": request.actor_id,
            "created_at": now.isoformat(),
        }

        transition_result = (
            self.db.table("sews_state_transitions")
            .insert(transition_row)
            .execute()
        )
        if not transition_result.data:
            raise SEWSWarningLedgerError(
                "State transition insert returned no row."
            )
        transition = transition_result.data[0]

        update_result = (
            self.db.table("sews_warning_problems")
            .update(
                {
                    "state": to_state.value,
                    "updated_at": now.isoformat(),
                }
            )
            .eq("id", problem["id"])
            .execute()
        )
        if not update_result.data:
            # Best-effort compensation because REST operations are not a
            # database transaction.
            self.db.table("sews_state_transitions").delete().eq(
                "id", transition["id"]
            ).execute()
            raise SEWSWarningLedgerError(
                "Warning problem state update returned no row."
            )

        return StateTransitionResponse(
            problem_key=problem_key,
            warning_problem_id=problem["id"],
            assessment_id=request.assessment_id,
            transition_id=transition["id"],
            from_state=from_state,
            to_state=to_state,
            transitioned=True,
            reason=request.reason,
            created_at=transition["created_at"],
        )

    def _next_version(self, warning_problem_id: str) -> int:
        result = (
            self.db.table("sews_warning_ledger")
            .select("version")
            .eq("warning_problem_id", warning_problem_id)
            .order("version", desc=True)
            .limit(1)
            .execute()
        )
        if not result.data:
            return 1
        return int(result.data[0]["version"]) + 1

    @staticmethod
    def _ledger_number(problem_key: str, version: int) -> str:
        # Deterministic, readable, and unique because the DB also enforces
        # uniqueness on warning_problem_id + version.
        year = datetime.now(timezone.utc).year
        compact_key = problem_key.removeprefix("WP-")
        return f"SW-{year}-{compact_key}-V{version:03d}"

    @staticmethod
    def _default_header(
        problem: dict[str, Any],
        assessment: dict[str, Any],
    ) -> dict[str, Any]:
        payload = assessment.get("deterministic_payload") or {}
        return {
            "problem_key": problem["problem_key"],
            "title": problem["title"],
            "hypothesis": problem["hypothesis"],
            "state": assessment["recommended_state"],
            "probability": assessment["probability"],
            "probability_band": assessment["probability_band"],
            "confidence_score": assessment["confidence_score"],
            "confidence_level": assessment["confidence_level"],
            "severity_score": assessment["severity_score"],
            "horizon_days": problem["horizon_days"],
            "assessed_at": assessment["assessed_at"],
            "formula_version": assessment["formula_version"],
            "direction": payload.get("direction"),
            "supporting_count": payload.get("supporting_count"),
            "contradicting_count": payload.get("contradicting_count"),
            "dark_or_stale_count": payload.get("dark_or_stale_count"),
        }

    def create_ledger_entry(
        self,
        problem_key: str,
        request: WarningLedgerCreateRequest,
    ) -> WarningLedgerResponse:
        problem = self._problem(problem_key)
        assessment = self._assessment(
            assessment_id=request.assessment_id,
            warning_problem_id=problem["id"],
        )

        existing = (
            self.db.table("sews_warning_ledger")
            .select("*")
            .eq("assessment_id", str(request.assessment_id))
            .limit(1)
            .execute()
        )
        if existing.data:
            return self._to_response(problem_key, existing.data[0])

        version = self._next_version(problem["id"])
        ledger_number = self._ledger_number(problem_key, version)
        now = datetime.now(timezone.utc)

        header = (
            request.deterministic_header
            or self._default_header(problem, assessment)
        )

        row = {
            "warning_problem_id": problem["id"],
            "ledger_number": ledger_number,
            "version": version,
            "assessment_id": str(request.assessment_id),
            "state": assessment["recommended_state"],
            "deterministic_header": header,
            "narrative_body": request.narrative_body,
            "published_at": now.isoformat() if request.publish else None,
            "created_at": now.isoformat(),
        }

        result = (
            self.db.table("sews_warning_ledger")
            .insert(row)
            .execute()
        )
        if not result.data:
            raise SEWSWarningLedgerError(
                "Warning ledger insert returned no row."
            )
        return self._to_response(problem_key, result.data[0])

    @staticmethod
    def _to_response(
        problem_key: str,
        row: dict[str, Any],
    ) -> WarningLedgerResponse:
        return WarningLedgerResponse(
            id=row["id"],
            warning_problem_id=row["warning_problem_id"],
            problem_key=problem_key,
            ledger_number=row["ledger_number"],
            version=row["version"],
            assessment_id=row["assessment_id"],
            state=row["state"],
            deterministic_header=row["deterministic_header"],
            narrative_body=row.get("narrative_body"),
            published_at=row.get("published_at"),
            created_at=row["created_at"],
        )

    def history(
        self,
        problem_key: str,
        *,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        problem = self._problem(problem_key)
        result = (
            self.db.table("sews_warning_ledger")
            .select("*")
            .eq("warning_problem_id", problem["id"])
            .order("version", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    def transitions(
        self,
        problem_key: str,
        *,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        problem = self._problem(problem_key)
        result = (
            self.db.table("sews_state_transitions")
            .select("*")
            .eq("warning_problem_id", problem["id"])
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
