from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


class ProblemState(str, Enum):
    DORMANT = "DORMANT"
    WATCH = "WATCH"
    ADVISORY = "ADVISORY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    RESOLVED = "RESOLVED"
    FALSIFIED = "FALSIFIED"


class IndicatorClass(str, Enum):
    PRECURSOR = "PRECURSOR"
    ACCELERANT = "ACCELERANT"
    TRIGGER = "TRIGGER"
    CONTRA = "CONTRA"


class IndicatorStatus(str, Enum):
    QUIET = "QUIET"
    STIRRING = "STIRRING"
    ACTIVE = "ACTIVE"
    CONTRADICTING = "CONTRADICTING"
    DARK = "DARK"


class IndicatorInput(BaseModel):
    indicator_key: str
    indicator_class: IndicatorClass = Field(alias="class")
    status: IndicatorStatus
    weight: float = Field(ge=0, le=5)
    baseline_z: float | None = None
    age_days: float = Field(default=0, ge=0)
    decay_half_life_days: float = Field(default=21, gt=0)
    source_count: int = Field(default=1, ge=0)
    source_domains: int = Field(default=1, ge=0)
    reporting: bool = True

    model_config = {"populate_by_name": True}


class AssessmentRequest(BaseModel):
    problem_key: str
    base_rate: float = Field(gt=0, lt=1)
    current_state: ProblemState
    severity_score: float = Field(ge=0, le=100)
    indicators: list[IndicatorInput]
    model_agreement: float = Field(default=0.75, ge=0, le=1)


class ConfidenceBreakdown(BaseModel):
    source_diversity: float
    indicator_coverage: float
    collection_integrity: float
    model_agreement: float
    freshness: float


class AssessmentResult(BaseModel):
    problem_key: str
    assessed_at: datetime
    probability: float
    probability_band: str
    confidence_score: float
    confidence_level: Literal["LOW", "MEDIUM", "HIGH"]
    severity_score: float
    recommended_state: ProblemState
    indicator_contributions: list[dict[str, Any]]
    confidence_breakdown: ConfidenceBreakdown
    formula_version: str = "sews-logit-v1"
