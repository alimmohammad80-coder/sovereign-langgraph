from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .models import ConfidenceAssessment, CrossModuleDestination, EvidenceStatus
from .phase5_models import HybridCampaignAssessment, HybridSignal


class ForecastHorizon(str, Enum):
    DAYS_7 = "7d"
    DAYS_30 = "30d"
    DAYS_90 = "90d"


class ForecastBand(BaseModel):
    horizon: ForecastHorizon
    probability: float = Field(ge=0, le=1)
    lower_bound: float = Field(ge=0, le=1)
    upper_bound: float = Field(ge=0, le=1)
    confidence: ConfidenceAssessment
    drivers: list[str] = Field(default_factory=list)
    indicators_to_watch: list[str] = Field(default_factory=list)


class EarlyWarningLevel(str, Enum):
    ROUTINE = "routine"
    WATCH = "watch"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class CyberHybridForecast(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    schema_version: str = "cyber-hybrid-forecast-v1"
    formula_version: str = "cyber-hybrid-logit-v1"
    title: str
    escalation: list[ForecastBand]
    persistence: list[ForecastBand]
    warning_score: float = Field(ge=0, le=100)
    warning_level: EarlyWarningLevel
    evidence_status: EvidenceStatus = EvidenceStatus.ASSESSED
    destinations: list[CrossModuleDestination] = Field(default_factory=list)
    supporting_signal_ids: list[UUID] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ForecastRequest(BaseModel):
    assessment: HybridCampaignAssessment
    recent_signals: list[HybridSignal] = Field(default_factory=list)
    prior_escalation_rate: float = Field(default=0.12, ge=0.001, le=0.95)
    prior_persistence_rate: float = Field(default=0.55, ge=0.01, le=0.99)
