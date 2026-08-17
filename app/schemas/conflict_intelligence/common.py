from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReviewStatus(str, Enum):
    VALIDATED = "validated"
    PROVISIONAL = "provisional"
    REQUIRES_REVIEW = "requires_review"
    REJECTED = "rejected"


class ConfidenceGrade(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class ConflictState(str, Enum):
    S0_STABLE = "S0_STABLE"
    S1_TENSION = "S1_TENSION"
    S2_CRISIS = "S2_CRISIS"
    S3_LIMITED_CONFLICT = "S3_LIMITED_CONFLICT"
    S4_WAR = "S4_WAR"
    S5_FROZEN = "S5_FROZEN"


class SeverityTier(str, Enum):
    MINIMAL = "Minimal"
    GUARDED = "Guarded"
    ELEVATED = "Elevated"
    HIGH = "High"
    CRITICAL = "Critical"


STATE_TO_SEVERITY: dict[ConflictState, SeverityTier] = {
    ConflictState.S0_STABLE: SeverityTier.MINIMAL,
    ConflictState.S1_TENSION: SeverityTier.GUARDED,
    ConflictState.S2_CRISIS: SeverityTier.ELEVATED,
    ConflictState.S3_LIMITED_CONFLICT: SeverityTier.HIGH,
    ConflictState.S4_WAR: SeverityTier.CRITICAL,
    ConflictState.S5_FROZEN: SeverityTier.GUARDED,
}


class SourceMetadata(BaseModel):
    source: str = Field(min_length=1)
    source_version: str | None = None
    confidence_grade: ConfidenceGrade = ConfidenceGrade.UNKNOWN
    review_status: ReviewStatus = ReviewStatus.REQUIRES_REVIEW
    last_reviewed: datetime | None = None


class APIError(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    status: str = "success"
    data: T
    meta: dict[str, Any] | None = None


class PaginationMeta(BaseModel):
    limit: int
    offset: int
    count: int


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RegistryRecord(ORMModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
