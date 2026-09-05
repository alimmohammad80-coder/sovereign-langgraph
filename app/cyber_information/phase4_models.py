from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .models import ConfidenceAssessment, EvidenceStatus, SourceProvenance


class NarrativeStatus(str, Enum):
    EMERGING = "emerging"
    ACTIVE = "active"
    ACCELERATING = "accelerating"
    DECLINING = "declining"
    DORMANT = "dormant"


class CoordinationLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class InformationObservation(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    schema_version: str = "information-observation-v1"
    text: str
    title: str | None = None
    source: str
    source_record_id: str | None = None
    source_domain: str | None = None
    source_country: str | None = None
    language: str | None = None
    platform: str | None = None
    author_or_account: str | None = None
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    published_at: datetime | None = None
    url: str | None = None
    countries: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: list[SourceProvenance] = Field(default_factory=list)


class NarrativeCluster(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    schema_version: str = "narrative-cluster-v1"
    label: str
    representative_text: str
    observation_ids: list[UUID] = Field(default_factory=list)
    observation_count: int = Field(default=0, ge=0)
    first_observed_at: datetime | None = None
    last_observed_at: datetime | None = None
    status: NarrativeStatus = NarrativeStatus.ACTIVE
    similarity_threshold: float = Field(default=0.45, ge=0, le=1)
    average_similarity: float = Field(default=0, ge=0, le=1)
    countries: list[str] = Field(default_factory=list)
    source_domains: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)
    velocity_score: float = Field(default=0, ge=0, le=100)
    reach_score: float = Field(default=0, ge=0, le=100)
    strategic_relevance_score: float = Field(default=0, ge=0, le=100)
    evidence_status: EvidenceStatus = EvidenceStatus.OBSERVED
    confidence: ConfidenceAssessment


class NarrativeEvolutionPoint(BaseModel):
    observed_at: datetime
    text: str
    source: str
    source_domain: str | None = None
    lexical_similarity_to_origin: float = Field(ge=0, le=1)
    mutation_score: float = Field(ge=0, le=100)


class NarrativeEvolution(BaseModel):
    cluster_id: UUID
    origin_text: str
    points: list[NarrativeEvolutionPoint] = Field(default_factory=list)
    mutation_count: int = Field(default=0, ge=0)
    max_mutation_score: float = Field(default=0, ge=0, le=100)
    evolution_direction: str = "stable"


class PropagationAssessment(BaseModel):
    cluster_id: UUID
    observation_count: int = Field(ge=0)
    distinct_sources: int = Field(ge=0)
    distinct_countries: int = Field(ge=0)
    distinct_platforms: int = Field(ge=0)
    elapsed_hours: float = Field(ge=0)
    velocity_score: float = Field(ge=0, le=100)
    reach_score: float = Field(ge=0, le=100)
    cross_platform_score: float = Field(ge=0, le=100)
    propagation_score: float = Field(ge=0, le=100)
    rationale: list[str] = Field(default_factory=list)


class CoordinationAssessment(BaseModel):
    cluster_id: UUID
    coordination_score: float = Field(ge=0, le=100)
    coordination_level: CoordinationLevel
    temporal_synchrony_score: float = Field(ge=0, le=100)
    text_similarity_score: float = Field(ge=0, le=100)
    source_diversity_score: float = Field(ge=0, le=100)
    account_reuse_score: float = Field(ge=0, le=100)
    evidence_status: EvidenceStatus = EvidenceStatus.INFERRED
    confidence: ConfidenceAssessment
    indicators: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


class InformationCampaign(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    schema_version: str = "information-campaign-v1"
    name: str
    narrative_cluster_ids: list[UUID] = Field(default_factory=list)
    status: NarrativeStatus
    first_observed_at: datetime | None = None
    last_observed_at: datetime | None = None
    countries: list[str] = Field(default_factory=list)
    source_domains: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)
    propagation_score: float = Field(ge=0, le=100)
    coordination_score: float = Field(ge=0, le=100)
    strategic_relevance_score: float = Field(ge=0, le=100)
    manipulation_likelihood_score: float = Field(ge=0, le=100)
    evidence_status: EvidenceStatus = EvidenceStatus.ASSESSED
    confidence: ConfidenceAssessment
    analytic_judgments: list[str] = Field(default_factory=list)
    provenance: list[SourceProvenance] = Field(default_factory=list)
