from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class EvidenceStatus(str, Enum):
    RAW = "RAW"
    NORMALIZED = "NORMALIZED"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"


class EvidencePolarity(str, Enum):
    SUPPORTING = "SUPPORTING"
    CONTRADICTING = "CONTRADICTING"
    NEUTRAL = "NEUTRAL"


class ObservationStatus(str, Enum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"


class ObservationTrend(str, Enum):
    RISING = "RISING"
    STABLE = "STABLE"
    FALLING = "FALLING"
    VOLATILE = "VOLATILE"
    UNKNOWN = "UNKNOWN"


class IndicatorStateStatus(str, Enum):
    ACTIVE = "ACTIVE"
    STALE = "STALE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    DEGRADED = "DEGRADED"
    INACTIVE = "INACTIVE"


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class EvidenceIngestRequest(ORMModel):
    source_key: str = Field(min_length=2, max_length=100)
    source_external_id: str | None = Field(default=None, max_length=500)
    canonical_url: HttpUrl | None = None
    title: str | None = Field(default=None, max_length=1000)
    raw_text: str | None = None
    raw_payload: dict[str, Any] | list[Any] | None = None
    content_type: str | None = Field(default=None, max_length=120)
    language_code: str | None = Field(default=None, min_length=2, max_length=12)
    published_at: datetime | None = None
    observed_at: datetime | None = None
    collector_agent: str | None = Field(default=None, max_length=200)
    collection_run_id: UUID | None = None
    country_iso3: str | None = Field(default=None, min_length=3, max_length=3)
    region_key: str | None = Field(default=None, max_length=120)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("country_iso3")
    @classmethod
    def normalize_iso3(cls, value: str | None) -> str | None:
        return value.upper() if value else None

    @field_validator("raw_text", "raw_payload")
    @classmethod
    def at_least_one_content_field(cls, value: Any, info):
        return value


class EvidenceIngestResponse(ORMModel):
    id: UUID
    evidence_key: str
    duplicate: bool = False
    status: EvidenceStatus


class EvidenceNormalizeRequest(ORMModel):
    raw_evidence_id: UUID
    evidence_type: str = Field(min_length=2, max_length=120)
    event_type: str | None = Field(default=None, max_length=160)
    summary: str | None = None
    normalized_text: str | None = None
    event_time: datetime | None = None
    country_iso3: str | None = Field(default=None, min_length=3, max_length=3)
    region_key: str | None = Field(default=None, max_length=120)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    entity_ids: list[UUID] = Field(default_factory=list)
    relationship_ids: list[UUID] = Field(default_factory=list)
    kg_evidence_id: UUID | None = None
    polarity: EvidencePolarity = EvidencePolarity.NEUTRAL
    source_reliability: float = Field(ge=0, le=100)
    extraction_confidence: float = Field(ge=0, le=100)
    validation_confidence: float | None = Field(default=None, ge=0, le=100)
    duplicate_cluster_key: str | None = None
    contradiction_cluster_key: str | None = None
    extractor_version: str | None = Field(default=None, max_length=100)
    validator_version: str | None = Field(default=None, max_length=100)
    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("country_iso3")
    @classmethod
    def normalize_iso3(cls, value: str | None) -> str | None:
        return value.upper() if value else None


class EvidenceObjectResponse(ORMModel):
    id: UUID
    evidence_object_key: str
    raw_evidence_id: UUID
    status: EvidenceStatus


class ObservationEvidenceLinkInput(ORMModel):
    evidence_object_id: UUID
    polarity: EvidencePolarity = EvidencePolarity.SUPPORTING
    contribution_weight: float = Field(default=1.0, ge=0, le=10)
    confidence: float = Field(ge=0, le=100)
    rationale: str | None = None


class ObservationCreateRequest(ORMModel):
    indicator_key: str = Field(min_length=2, max_length=250)
    warning_problem_key: str | None = Field(default=None, max_length=250)
    analytic_framework_key: str | None = Field(default=None, max_length=250)
    indicator_group_key: str | None = Field(default=None, max_length=250)
    title: str = Field(min_length=3, max_length=1000)
    statement: str = Field(min_length=3)
    normalized_value: float | None = Field(default=None, ge=0, le=1)
    raw_value: float | None = None
    unit: str | None = Field(default=None, max_length=100)
    polarity: EvidencePolarity = EvidencePolarity.NEUTRAL
    trend: ObservationTrend = ObservationTrend.UNKNOWN
    confidence: float = Field(ge=0, le=100)
    observed_at: datetime
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    country_iso3: str | None = Field(default=None, min_length=3, max_length=3)
    region_key: str | None = Field(default=None, max_length=120)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    status: ObservationStatus = ObservationStatus.VALIDATED
    generation_method: Literal["RULE_BASED", "ANALYST", "LLM_EXTRACTED"] = "RULE_BASED"
    generator_version: str | None = Field(default=None, max_length=100)
    analyst_reviewed: bool = False
    reviewed_by: str | None = Field(default=None, max_length=200)
    reviewed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    evidence_links: list[ObservationEvidenceLinkInput] = Field(min_length=1)

    @field_validator("country_iso3")
    @classmethod
    def normalize_iso3(cls, value: str | None) -> str | None:
        return value.upper() if value else None


class ObservationResponse(ORMModel):
    id: UUID
    observation_key: str
    indicator_key: str
    status: ObservationStatus
    evidence_count: int
    corroborated_source_count: int
    source_reliability_mean: float | None
    freshness_score: float | None


class IndicatorStateRecalculateRequest(ORMModel):
    indicator_key: str = Field(min_length=2, max_length=250)
    warning_problem_key: str | None = Field(default=None, max_length=250)
    analytic_framework_key: str | None = Field(default=None, max_length=250)
    indicator_group_key: str | None = Field(default=None, max_length=250)
    country_iso3: str | None = Field(default=None, min_length=3, max_length=3)
    region_key: str | None = Field(default=None, max_length=120)
    lookback_days: int = Field(default=30, ge=1, le=3650)
    stale_after_hours: int = Field(default=72, ge=1, le=8760)
    minimum_evidence: int = Field(default=2, ge=1, le=1000)

    @field_validator("country_iso3")
    @classmethod
    def normalize_iso3(cls, value: str | None) -> str | None:
        return value.upper() if value else None


class IndicatorStateResponse(ORMModel):
    id: UUID
    state_key: str
    indicator_key: str
    current_value: float | None
    previous_value: float | None
    delta: float | None
    trend: ObservationTrend
    confidence: float
    evidence_count: int
    supporting_evidence_count: int
    contradicting_evidence_count: int
    corroborated_source_count: int
    freshness_score: float
    status: IndicatorStateStatus
    last_observed_at: datetime | None
    last_calculated_at: datetime
    calculation_version: str


class WarningProblemStateResponse(ORMModel):
    warning_problem_key: str
    indicator_count: int
    active_count: int
    insufficient_evidence_count: int
    degraded_count: int
    stale_count: int
    mean_value: float | None
    mean_confidence: float | None
    states: list[dict[str, Any]]
