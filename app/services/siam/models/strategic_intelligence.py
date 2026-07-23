from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class StrategicIntelligence:
    """
    Canonical output produced by SIAM cross-domain fusion.

    This model represents integrated strategic judgment rather than
    an individual domain-agent assessment or a generated report.
    """

    region: str

    title: str
    bluf: str
    executive_judgment: str

    risk_score: float
    risk_level: str
    confidence: float
    analytical_status: str

    leading_domain: str | None = None
    strategic_direction: str = "stable"

    domain_assessments: list[dict[str, Any]] = field(
        default_factory=list
    )
    key_drivers: list[dict[str, Any]] = field(
        default_factory=list
    )
    cross_domain_dynamics: list[dict[str, Any]] = field(
        default_factory=list
    )
    convergence_findings: list[dict[str, Any]] = field(
        default_factory=list
    )
    contradictions: list[dict[str, Any]] = field(
        default_factory=list
    )

    forecast_probabilities: dict[str, float] = field(
        default_factory=dict
    )
    alternative_hypotheses: list[dict[str, Any]] = field(
        default_factory=list
    )
    implications: list[str] = field(
        default_factory=list
    )
    recommended_actions: list[str] = field(
        default_factory=list
    )
    intelligence_gaps: list[str] = field(
        default_factory=list
    )
    watch_indicators: list[dict[str, Any]] = field(
        default_factory=list
    )

    coverage: dict[str, Any] = field(
        default_factory=dict
    )
    evidence_composition: dict[str, int] = field(
        default_factory=dict
    )
    methodology: dict[str, str] = field(
        default_factory=lambda: {
            "name": "Sovereign Intelligence Analytical Methodology",
            "version": "SIAM-1.0-draft",
        }
    )
    provenance: dict[str, Any] = field(
        default_factory=dict
    )

    generated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "region": self.region,
            "title": self.title,
            "bluf": self.bluf,
            "executive_judgment": self.executive_judgment,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "confidence": self.confidence,
            "analytical_status": self.analytical_status,
            "leading_domain": self.leading_domain,
            "strategic_direction": self.strategic_direction,
            "domain_assessments": self.domain_assessments,
            "key_drivers": self.key_drivers,
            "cross_domain_dynamics": self.cross_domain_dynamics,
            "convergence_findings": self.convergence_findings,
            "contradictions": self.contradictions,
            "forecast_probabilities": self.forecast_probabilities,
            "alternative_hypotheses": self.alternative_hypotheses,
            "implications": self.implications,
            "recommended_actions": self.recommended_actions,
            "intelligence_gaps": self.intelligence_gaps,
            "watch_indicators": self.watch_indicators,
            "coverage": self.coverage,
            "evidence_composition": self.evidence_composition,
            "methodology": self.methodology,
            "provenance": self.provenance,
            "generated_at": self.generated_at,
        }
