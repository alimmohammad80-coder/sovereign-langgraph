from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client

from app.routes.sews_evidence import get_sews_supabase_client
from app.schemas.sews_warning_ledger import (
    StateTransitionRequest,
    StateTransitionResponse,
    WarningHistoryResponse,
    WarningLedgerCreateRequest,
    WarningLedgerResponse,
)
from app.services.sews_warning_ledger_service import (
    SEWSWarningLedgerError,
    SEWSWarningLedgerService,
)


router = APIRouter(
    prefix="/api/sews/warning-problems",
    tags=["SEWS Warning Ledger"],
)


def get_db() -> Client:
    return get_sews_supabase_client()


def _unprocessable(exc: Exception) -> None:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=str(exc),
    ) from exc


@router.post(
    "/{problem_key}/transition",
    response_model=StateTransitionResponse,
)
def transition_warning_problem(
    problem_key: str,
    payload: StateTransitionRequest,
    db: Client = Depends(get_db),
):
    try:
        return SEWSWarningLedgerService(db).transition(
            problem_key,
            payload,
        )
    except SEWSWarningLedgerError as exc:
        _unprocessable(exc)


@router.post(
    "/{problem_key}/ledger",
    response_model=WarningLedgerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_warning_ledger_entry(
    problem_key: str,
    payload: WarningLedgerCreateRequest,
    db: Client = Depends(get_db),
):
    try:
        return SEWSWarningLedgerService(db).create_ledger_entry(
            problem_key,
            payload,
        )
    except SEWSWarningLedgerError as exc:
        _unprocessable(exc)


@router.get(
    "/{problem_key}/ledger",
    response_model=WarningHistoryResponse,
)
def warning_ledger_history(
    problem_key: str,
    db: Client = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, Any]:
    try:
        data = SEWSWarningLedgerService(db).history(
            problem_key,
            limit=limit,
        )
        return {
            "problem_key": problem_key,
            "count": len(data),
            "data": data,
        }
    except SEWSWarningLedgerError as exc:
        _unprocessable(exc)


@router.get(
    "/{problem_key}/transitions",
    response_model=WarningHistoryResponse,
)
def warning_transition_history(
    problem_key: str,
    db: Client = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    try:
        data = SEWSWarningLedgerService(db).transitions(
            problem_key,
            limit=limit,
        )
        return {
            "problem_key": problem_key,
            "count": len(data),
            "data": data,
        }
    except SEWSWarningLedgerError as exc:
        _unprocessable(exc)
