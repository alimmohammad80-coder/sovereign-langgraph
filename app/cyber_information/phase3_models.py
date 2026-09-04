from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .models import ConfidenceAssessment, EvidenceStatus, SourceProvenance


class CyberIncidentType(str, Enum):
    EXPLOITATION = "exploitation"
    MALWARE_ACTIVITY = "malware_activity"
    PHISHING = "phishing"
    RANSOMWARE = "ransomware"
    DDOS = "ddos"
    CREDENTIAL_ATTACK = "credential_attack"
    INTRUSION = "intrusion"
    INFRASTRUCTURE_ABUSE = "infrastructure_abuse"
    VULNERABILITY_DISCLOSURE = "vulnerability_disclosure"
    ADVISORY = "advisory"
    UNKNOWN = "unknown"


class ExposureLevel(str, Enum):
    LOW = "low"
    GUARDED = "guarded"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"


class CyberIncident(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    schema_version: str = "cyber-incident-v1"
    incident_type: CyberIncidentType
    title: str
    summary: str
    source: str
    source_record_id: str | None = None
    evidence_status: EvidenceStatus = EvidenceStatus.OBSERVED
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    occurred_at: datetime | None = None
    countries: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    cves: list[str] = Field(default_factory=list)
    attack_techniques: list[str] = Field(default_factory=list)
    indicators: list[dict[str, Any]] = Field(default_factory=list)
    suspected_actors: list[str] = Field(default_factory=list)
    campaign_names: list[str] = Field(default_factory=list)
    target_names: list[str] = Field(default_factory=list)
    severity_score: float = Field(ge=0, le=100)
    confidence: ConfidenceAssessment
    provenance: list[SourceProvenance] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VulnerabilityExposure(BaseModel):
    cve_id: str
    vendor: str | None = None
    product: str | None = None
    known_exploited: bool = False
    known_ransomware_use: bool | None = None
    exposure_score: float = Field(ge=0, le=100)
    exposure_level: ExposureLevel
    severity_score: float = Field(ge=0, le=100)
    exploitability_score: float = Field(ge=0, le=100)
    target_criticality_score: float = Field(ge=0, le=100)
    evidence_status: EvidenceStatus
    confidence: ConfidenceAssessment
    provenance: list[SourceProvenance] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)


class InfrastructureTargetProfile(BaseModel):
    name: str
    sector: str
    country_iso3: str | None = None
    asset_type: str | None = None
    criticality_score: float = Field(ge=0, le=100)
    observed_incident_count: int = Field(default=0, ge=0)
    vulnerability_ids: list[str] = Field(default_factory=list)
    actor_names: list[str] = Field(default_factory=list)
    campaign_names: list[str] = Field(default_factory=list)
    targeting_score: float = Field(ge=0, le=100)
    confidence: ConfidenceAssessment


class ActorCampaignLink(BaseModel):
    actor_name: str
    campaign_name: str
    relationship: str = "associated_with"
    evidence_status: EvidenceStatus
    confidence: ConfidenceAssessment
    supporting_sources: list[str] = Field(default_factory=list)
    attack_techniques: list[str] = Field(default_factory=list)
    target_sectors: list[str] = Field(default_factory=list)
