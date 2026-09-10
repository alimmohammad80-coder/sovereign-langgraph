from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


SEWS_OFFICIAL_ASSESSMENT_FORMAT = "SEWS-OA/2.0"


class ProductGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessment_id: UUID
    ai_review_id: UUID | None = None
    product_type: str = Field(default="SEWS_WARNING", max_length=100)
    audience: str = Field(default="EXECUTIVE", max_length=100)
    publish_to_ledger: bool = True
    publish_product: bool = False
    preferred_provider: str | None = None
    preferred_model: str | None = None


class OfficialAssessmentForecast(BaseModel):
    near_term_0_30_days: str = ""
    medium_term_31_90_days: str = ""
    longer_term_91_180_days: str = ""


class OfficialAssessmentSections(BaseModel):
    """Canonical reader-facing structure shared by every SEWS warning problem."""

    key_judgment: str
    why_it_matters: str
    what_is_happening: str
    why_we_assess_this: str
    countervailing_evidence: str
    escalation_pathway: str
    implications: str
    uncertainty_and_gaps: str
    what_to_watch_next: list[str] = Field(default_factory=list)
    forecast: OfficialAssessmentForecast = Field(default_factory=OfficialAssessmentForecast)


class StrategicIntelligenceProduct(BaseModel):
    product_id: UUID | None = None
    product_key: str
    product_type: str
    problem_key: str
    assessment_id: UUID
    ai_review_id: UUID | None = None

    # New products use the versioned Official Assessment contract. Legacy rows
    # remain valid and readable; they are never silently relabeled as OA/2.0.
    report_format_version: str = "SEWS-LEGACY/1.0"
    report_sections: OfficialAssessmentSections | None = None

    title: str
    bluf: str
    executive_summary: str
    official_assessment: dict[str, Any]
    ai_strategic_review: dict[str, Any] | None = None
    drivers: list[dict[str, Any]]
    contrary_evidence: list[dict[str, Any]]
    confidence_and_provenance: dict[str, Any]
    historical_analogs: list[dict[str, Any]]
    monitoring_priorities: list[str]
    forecast: dict[str, Any]
    full_analysis: str

    quality_assurance: dict[str, Any]
    publication: dict[str, Any]
    created_at: datetime
    published_at: datetime | None = None

    @field_validator("bluf")
    @classmethod
    def validate_bluf(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("BLUF cannot be empty.")
        return text

    @field_validator("full_analysis")
    @classmethod
    def validate_analysis(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Full analysis cannot be empty.")
        return text


class ProductHistoryResponse(BaseModel):
    problem_key: str
    count: int
    data: list[dict[str, Any]]
