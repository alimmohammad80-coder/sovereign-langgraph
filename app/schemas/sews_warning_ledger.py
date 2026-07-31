from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.sews_warning_scoring import WarningState


class StateTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessment_id: UUID
    reason: str = Field(min_length=3, max_length=3000)
    actor_type: str = Field(default="SYSTEM", pattern="^(SYSTEM|ANALYST)$")
    actor_id: str | None = Field(default=None, max_length=250)
    force: bool = False


class StateTransitionResponse(BaseModel):
    problem_key: str
    warning_problem_id: UUID
    assessment_id: UUID
    transition_id: UUID | None = None
    from_state: WarningState
    to_state: WarningState
    transitioned: bool
    reason: str
    created_at: datetime | None = None


class WarningLedgerCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessment_id: UUID
    deterministic_header: dict[str, Any] | None = None
    narrative_body: dict[str, Any] | None = None
    publish: bool = False


class WarningLedgerResponse(BaseModel):
    id: UUID
    warning_problem_id: UUID
    problem_key: str
    ledger_number: str
    version: int
    assessment_id: UUID
    state: WarningState
    deterministic_header: dict[str, Any]
    narrative_body: dict[str, Any] | None
    published_at: datetime | None
    created_at: datetime


class WarningHistoryResponse(BaseModel):
    problem_key: str
    count: int
    data: list[dict[str, Any]]
