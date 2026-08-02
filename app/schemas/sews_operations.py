from __future__ import annotations
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

class WarningSupervisorRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    problem_key: str
    dry_run: bool = False
    limit_per_query: int = Field(default=10, ge=1, le=100)

class PortfolioSupervisorRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    problem_keys: list[str] | None = None
    dry_run: bool = False
    concurrency: int = Field(default=3, ge=1, le=10)
    limit_per_query: int = Field(default=10, ge=1, le=100)

class IndicatorPipelineSummary(BaseModel):
    indicator_key: str
    matched_evidence_count: int = 0
    observations_created: int = 0
    state_recalculated: bool = False
    state_status: str | None = None
    current_value: float | None = None
    confidence: float | None = None
    error: str | None = None

class EvidencePipelineResponse(BaseModel):
    status: str
    problem_key: str
    records_received: int = 0
    records_persisted: int = 0
    indicators_considered: int = 0
    indicators_matched: int = 0
    observations_created: int = 0
    states_recalculated: int = 0
    assessment_id: str | None = None
    assessment_probability: float | None = None
    assessment_confidence: float | None = None
    assessment_state: str | None = None
    material_change: bool = False
    material_change_reasons: list[str] = Field(default_factory=list)
    ai_review_id: str | None = None
    product_id: str | None = None
    errors: list[str] = Field(default_factory=list)
    indicator_results: list[IndicatorPipelineSummary] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

class PortfolioSupervisorRunResponse(BaseModel):
    status: str
    total_warning_problems: int
    completed: int
    failed: int
    material_changes: int
    results: list[EvidencePipelineResponse]
