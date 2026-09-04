from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class IntelligenceDomain(str, Enum):
    CYBER = "cyber"
    INFORMATION = "information_operations"
    HYBRID = "hybrid"


class EntityType(str, Enum):
    STATE = "state"
    THREAT_ACTOR = "threat_actor"
    ORGANIZATION = "organization"
    PERSON = "person"
    CAMPAIGN = "campaign"
    MALWARE = "malware"
    VULNERABILITY = "vulnerability"
    INFRASTRUCTURE = "infrastructure"
    SECTOR = "sector"
    NARRATIVE = "narrative"
    PLATFORM = "platform"
    LOCATION = "location"
    INCIDENT = "incident"


class RelationshipType(str, Enum):
    ATTRIBUTED_TO = "attributed_to"
    TARGETS = "targets"
    USES = "uses"
    EXPLOITS = "exploits"
    AMPLIFIES = "amplifies"
    ORIGINATES_FROM = "originates_from"
    AFFECTS = "affects"
    PART_OF = "part_of"
    CORRELATED_WITH = "correlated_with"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"


class EvidenceStatus(str, Enum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    ASSESSED = "assessed"


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class SourceProvenance(BaseModel):
    source_name: str
    source_type: str
    source_url: str | None = None
    publisher: str | None = None
    published_at: datetime | None = None
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_record_id: str | None = None
    retrieval_method: str | None = None
    content_hash: str | None = None
    reliability_score: float | None = Field(default=None, ge=0, le=1)


class ConfidenceAssessment(BaseModel):
    score: float = Field(ge=0, le=1)
    level: ConfidenceLevel
    evidence_quality: float = Field(ge=0, le=1)
    source_diversity: float = Field(ge=0, le=1)
    corroboration: float = Field(ge=0, le=1)
    analytic_uncertainty: float = Field(ge=0, le=1)
    rationale: str


class IntelligenceEntity(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    entity_type: EntityType
    name: str
    aliases: list[str] = Field(default_factory=list)
    country_iso3: str | None = Field(default=None, min_length=3, max_length=3)
    attributes: dict[str, Any] = Field(default_factory=dict)


class IntelligenceRelationship(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    source_entity_id: UUID
    target_entity_id: UUID
    relationship_type: RelationshipType
    evidence_status: EvidenceStatus
    confidence: ConfidenceAssessment
    provenance: list[SourceProvenance] = Field(default_factory=list)
    first_observed_at: datetime | None = None
    last_observed_at: datetime | None = None


class CrossModuleDestination(str, Enum):
    COUNTRY_INTELLIGENCE = "country_intelligence"
    CONFLICT_FORECASTING = "conflict_forecasting"
    STRATEGIC_EARLY_WARNING = "strategic_early_warning"
    SUPPLY_CHAIN_INTELLIGENCE = "supply_chain_intelligence"
    CORPORATE_FINANCIAL_RISK = "corporate_financial_risk"
    GLOBAL_RISK_MAP = "global_risk_map"
    INTELLIGENCE_STREAM = "intelligence_stream"
    STRATEGIC_AI_AGENTS = "strategic_ai_agents"


class CrossModuleEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    schema_version: str = "cyber-info-event-v1"
    domain: IntelligenceDomain
    event_type: str
    title: str
    summary: str
    evidence_status: EvidenceStatus
    occurred_at: datetime | None = None
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    countries: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    entity_ids: list[UUID] = Field(default_factory=list)
    severity_score: float = Field(ge=0, le=100)
    confidence: ConfidenceAssessment
    provenance: list[SourceProvenance] = Field(default_factory=list)
    destinations: list[CrossModuleDestination] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
