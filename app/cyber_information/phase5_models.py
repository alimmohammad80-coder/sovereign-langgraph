from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .models import ConfidenceAssessment, EvidenceStatus
from .phase3_models import CyberIncident, InfrastructureTargetProfile
from .phase4_models import InformationCampaign, InformationObservation


class HybridSignalDomain(str, Enum):
    CYBER = "cyber"
    INFORMATION = "information"
    MILITARY = "military"
    DIPLOMATIC = "diplomatic"
    ECONOMIC = "economic"
    INFRASTRUCTURE = "infrastructure"
    SUPPLY_CHAIN = "supply_chain"
    POLITICAL = "political"


class HybridSignal(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    domain: HybridSignalDomain
    title: str
    summary: str
    occurred_at: datetime | None = None
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    countries: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    actors: list[str] = Field(default_factory=list)
    targets: list[str] = Field(default_factory=list)
    severity_score: float = Field(default=50, ge=0, le=100)
    confidence: ConfidenceAssessment
    evidence_status: EvidenceStatus = EvidenceStatus.OBSERVED
    source_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FusionDimension(BaseModel):
    score: float = Field(ge=0, le=100)
    rationale: list[str] = Field(default_factory=list)


class HybridCampaignAssessment(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    schema_version: str = "hybrid-campaign-v1"
    title: str
    summary: str
    countries: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    actors: list[str] = Field(default_factory=list)
    targets: list[str] = Field(default_factory=list)
    signal_count: int = Field(ge=0)
    domains_present: list[HybridSignalDomain] = Field(default_factory=list)
    temporal_convergence: FusionDimension
    target_convergence: FusionDimension
    actor_convergence: FusionDimension
    geographic_convergence: FusionDimension
    cross_domain_convergence: FusionDimension
    infrastructure_relevance: FusionDimension
    hybrid_score: float = Field(ge=0, le=100)
    confidence: ConfidenceAssessment
    evidence_status: EvidenceStatus = EvidenceStatus.ASSESSED
    supporting_signal_ids: list[UUID] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class HybridFusionRequest(BaseModel):
    title: str = "Hybrid activity assessment"
    cyber_incidents: list[CyberIncident] = Field(default_factory=list)
    information_campaigns: list[InformationCampaign] = Field(default_factory=list)
    information_observations: list[InformationObservation] = Field(default_factory=list)
    infrastructure_profiles: list[InfrastructureTargetProfile] = Field(default_factory=list)
    external_signals: list[HybridSignal] = Field(default_factory=list)
