from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WarningState(StrEnum):
    DORMANT = "DORMANT"
    WATCH = "WATCH"
    ADVISORY = "ADVISORY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    RESOLVED = "RESOLVED"
    FALSIFIED = "FALSIFIED"


class WarningAssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    country_iso3: str | None = Field(default=None, min_length=3, max_length=3)
    region_key: str | None = Field(default=None, max_length=120)
    minimum_indicator_confidence: float = Field(default=30, ge=0, le=100)
    minimum_indicator_count: int = Field(default=2, ge=1, le=5000)
    persist: bool = True


class IndicatorContribution(BaseModel):
    indicator_key: str
    indicator_class: str
    current_value: float
    confidence: float
    weight: float
    polarity: float
    weighted_contribution: float
    status: str


class WarningAssessmentResponse(BaseModel):
    problem_key: str
    warning_problem_id: UUID
    assessed_at: datetime
    probability: float
    probability_band: str
    confidence_score: float
    confidence_level: str
    severity_score: float
    recommended_state: WarningState
    direction: str
    indicator_count: int
    supporting_count: int
    contradicting_count: int
    dark_or_stale_count: int
    indicator_contributions: list[IndicatorContribution]
    confidence_breakdown: dict[str, float]
    formula_version: str
    assessment_id: UUID | None = None
    persisted: bool = False
    deterministic_payload: dict[str, Any]
