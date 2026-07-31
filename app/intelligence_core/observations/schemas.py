from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class ObservationDirection(StrEnum):
    INCREASING = "INCREASING"
    DECREASING = "DECREASING"
    STABLE = "STABLE"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


class ObservationStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"


class MaterialityLevel(StrEnum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ObservationEntity(BaseModel):
    entity_type: str
    name: str
    canonical_name: str | None = None
    external_id: str | None = None
    country_iso3: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IndicatorImpact(BaseModel):
    indicator_key: str
    impact_score: float = Field(ge=-100.0, le=100.0)
    confidence: float = Field(ge=0.0, le=1.0)
    mapping_rule: str
    rationale: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("indicator_key", mode="before")
    @classmethod
    def normalize_indicator_key(cls, value: str) -> str:
        return str(value).strip().upper()


class IntelligenceObservation(BaseModel):
    observation_id: str = Field(
        default_factory=lambda: str(uuid4())
    )
    observation_key: str

    title: str
    summary: str
    observation_type: str

    source_key: str
    source_record_id: str | None = None
    evidence_id: str | None = None
    canonical_record_id: str | None = None

    country_iso3: str | None = None
    region_key: str | None = None

    direction: ObservationDirection = ObservationDirection.UNKNOWN
    severity: float = Field(default=0.0, ge=0.0, le=100.0)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source_reliability: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
    )
    novelty: float = Field(default=0.5, ge=0.0, le=1.0)

    materiality_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
    )
    materiality_level: MaterialityLevel = MaterialityLevel.LOW
    is_material: bool = False

    status: ObservationStatus = ObservationStatus.ACTIVE

    entities: list[ObservationEntity] = Field(default_factory=list)
    indicator_impacts: list[IndicatorImpact] = Field(
        default_factory=list
    )

    effective_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    expires_at: datetime | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "observation_key",
        "observation_type",
        "source_key",
        "country_iso3",
        "region_key",
        mode="before",
    )
    @classmethod
    def normalize_keys(cls, value: Any) -> Any:
        if value is None:
            return None
        return str(value).strip().upper()
