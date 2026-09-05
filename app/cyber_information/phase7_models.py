from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .models import ConfidenceAssessment, EvidenceStatus


class IntegrationDestination(str, Enum):
    STRATEGIC_EARLY_WARNING = "strategic_early_warning"
    CONFLICT_FORECASTING = "conflict_forecasting"
    COUNTRY_INTELLIGENCE = "country_intelligence"
    GLOBAL_RISK_MAP = "global_risk_map"
    INTELLIGENCE_STREAM = "intelligence_stream"
    STRATEGIC_AI_AGENTS = "strategic_ai_agents"
    SUPPLY_CHAIN_INTELLIGENCE = "supply_chain_intelligence"
    CORPORATE_FINANCIAL_RISK = "corporate_financial_risk"


class DeliveryState(str, Enum):
    PLANNED = "planned"
    SUPPRESSED = "suppressed"
    READY = "ready"
    DELIVERED = "delivered"
    FAILED = "failed"


class PlatformIntelligenceEnvelope(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    schema_version: str = "platform-intelligence-envelope-v1"
    source_module: str = "cyber_information_operations"
    source_object_type: str
    source_object_id: str
    title: str
    summary: str
    countries: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    actors: list[str] = Field(default_factory=list)
    targets: list[str] = Field(default_factory=list)
    severity_score: float = Field(ge=0, le=100)
    confidence: ConfidenceAssessment
    evidence_status: EvidenceStatus
    forecast_probability_30d: float | None = Field(default=None, ge=0, le=1)
    warning_level: str | None = None
    model_version: str | None = None
    calibration_status: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deduplication_key: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class DestinationPayload(BaseModel):
    destination: IntegrationDestination
    state: DeliveryState
    reason: str
    materiality_score: float = Field(ge=0, le=100)
    payload: dict[str, Any] = Field(default_factory=dict)


class IntegrationPlan(BaseModel):
    envelope: PlatformIntelligenceEnvelope
    routes: list[DestinationPayload] = Field(default_factory=list)
    suppressed_count: int = Field(default=0, ge=0)
    ready_count: int = Field(default=0, ge=0)


class DeliveryResult(BaseModel):
    destination: IntegrationDestination
    state: DeliveryState
    deduplication_key: str
    delivered_at: datetime | None = None
    error: str | None = None
    response_metadata: dict[str, Any] = Field(default_factory=dict)
