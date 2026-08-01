from __future__ import annotations
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

class SourceBridgeStatus(BaseModel):
    source_key: str
    available: bool
    selected_callable: str | None = None
    candidates_checked: list[str] = Field(default_factory=list)
    error: str | None = None

class BridgeRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    problem_keys: list[str] | None = None
    source_keys: list[str] | None = None
    limit_per_query: int = Field(default=10, ge=1, le=100)
    persist: bool = True
    dry_run: bool = False

class BridgeSourceResult(BaseModel):
    source_key: str
    available: bool
    queries_attempted: int = 0
    records_received: int = 0
    records_normalized: int = 0
    records_persisted: int = 0
    duplicates_skipped: int = 0
    errors: list[str] = Field(default_factory=list)

class BridgeRunResponse(BaseModel):
    status: str
    warning_problem_count: int
    source_results: list[BridgeSourceResult]
    total_records_received: int
    total_records_persisted: int
    metadata: dict[str, Any] = Field(default_factory=dict)
