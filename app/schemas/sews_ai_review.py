from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReviewDisposition(StrEnum):
    AGREE = "AGREE"
    MINOR_DISAGREEMENT = "MINOR_DISAGREEMENT"
    MAJOR_DISAGREEMENT = "MAJOR_DISAGREEMENT"
    CRITICAL_DIVERGENCE = "CRITICAL_DIVERGENCE"


class AIReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessment_id: UUID
    model_provider: str = Field(default="NVIDIA", max_length=80)
    model_name: str | None = Field(default=None, max_length=200)
    include_historical_analogs: bool = True
    include_monitoring_priorities: bool = True
    persist: bool = True


class AIReviewResponse(BaseModel):
    id: UUID | None = None
    problem_key: str
    assessment_id: UUID
    reviewed_at: datetime
    model_provider: str
    model_name: str
    official_probability: float
    official_confidence: float
    suggested_probability: float
    suggested_confidence: float
    probability_variance: float
    confidence_variance: float
    agreement_score: float
    disposition: ReviewDisposition
    recommended_state: str
    maintain_official_state: bool
    key_drivers: list[str]
    contrary_evidence: list[str]
    confidence_rationale: str
    monitoring_priorities: list[str]
    historical_analogs: list[dict[str, Any]]
    narrative: str
    raw_model_output: dict[str, Any]
    persisted: bool = False


class AssessmentComparisonResponse(BaseModel):
    problem_key: str
    assessment_id: UUID
    review_id: UUID
    official: dict[str, Any]
    ai_review: dict[str, Any]
    variance: dict[str, float]
    disposition: ReviewDisposition
    analyst_review_required: bool
