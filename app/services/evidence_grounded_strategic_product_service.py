from __future__ import annotations

from typing import Any

from app.services.sews_evidence_context_service import SEWSEvidenceContextService
from app.services.strategic_intelligence_product_service import (
    StrategicIntelligenceProductService,
)


class EvidenceGroundedStrategicIntelligenceProductService(
    StrategicIntelligenceProductService
):
    """Strategic product service with canonical source evidence in model context.

    Deterministic assessment values remain authoritative in the base service.
    This subclass only enriches the narrative context with evidence that is
    explicitly linked to the warning problem in the SEWS data model.
    """

    @staticmethod
    def _qualitative_ai_review(ai_review: dict[str, Any] | None) -> dict[str, Any] | None:
        if not ai_review:
            return None
        # Official SEWS products have one numerical authority: the deterministic
        # assessment. AI review can challenge assumptions qualitatively but its
        # alternative probability/confidence must never become a competing
        # official forecast in the report narrative.
        allowed = {
            "id",
            "reviewed_at",
            "model_provider",
            "model_name",
            "agreement_score",
            "disposition",
            "recommended_state",
            "maintain_official_state",
            "key_drivers",
            "contrary_evidence",
            "confidence_rationale",
            "monitoring_priorities",
            "historical_analogs",
            "narrative",
        }
        return {key: value for key, value in ai_review.items() if key in allowed}

    @staticmethod
    def _forecast_text(value: Any) -> str:
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, dict):
            for key in ("trajectory", "outlook", "narrative", "assessment", "summary", "text"):
                text = value.get(key)
                if isinstance(text, str) and text.strip():
                    return text.strip()
        return ""

    @classmethod
    def _canonical_forecast(cls, forecast: Any) -> dict[str, str]:
        source = forecast if isinstance(forecast, dict) else {}
        items = [(str(k).lower(), cls._forecast_text(v)) for k, v in source.items()]
        items = [(k, v) for k, v in items if v]

        def choose(words: tuple[str, ...], fallback_index: int) -> str:
            for key, value in items:
                if any(word in key for word in words):
                    return value
            return items[fallback_index][1] if len(items) > fallback_index else ""

        return {
            "near_term_0-30_days": choose(("near", "0-30", "0_30", "7", "30"), 0),
            "medium_term_31-90_days": choose(("medium", "31-90", "31_90", "60", "90"), 1),
            "longer_term_91-180_days": choose(("long", "longer", "91-180", "91_180", "120", "180"), 2),
        }

    @classmethod
    def _validate_model_payload(cls, payload: dict[str, Any]) -> dict[str, Any]:
        payload = super()._validate_model_payload(payload)
        payload["forecast"] = cls._canonical_forecast(payload.get("forecast"))
        return payload

    def _context_payload(
        self,
        problem: dict[str, Any],
        assessment: dict[str, Any],
        ai_review: dict[str, Any] | None,
        deterministic_drivers: list[dict[str, Any]],
        deterministic_contra: list[dict[str, Any]],
        request: Any,
    ) -> dict[str, Any]:
        context = super()._context_payload(
            problem,
            assessment,
            self._qualitative_ai_review(ai_review),
            deterministic_drivers,
            deterministic_contra,
            request,
        )

        evidence_context = SEWSEvidenceContextService(self.db).build(
            str(problem["problem_key"]),
            limit=40,
        )
        documents = evidence_context.get("documents") or []

        # Keep the model context compact and source-verifiable. Full raw rows
        # remain available through the evidence-context endpoint/UI.
        context["canonical_evidence"] = [
            {
                "evidence_object_id": row.get("evidence_object_id"),
                "source_name": row.get("source_name"),
                "source_key": row.get("source_key"),
                "title": row.get("title"),
                "summary": str(row.get("summary") or "")[:1800],
                "url": row.get("url"),
                "published_at": row.get("published_at") or row.get("event_time"),
                "status": row.get("status"),
                "reliability": row.get("reliability"),
                "validation_confidence": row.get("validation_confidence"),
                "freshness": row.get("freshness"),
                "indicator_keys": row.get("indicator_keys") or [],
                "observation_statements": row.get("observation_statements") or [],
            }
            for row in documents[:24]
        ]
        context["evidence_quality"] = evidence_context.get("quality") or {}
        context["reporting_standard"] = {
            "single_probability_authority": (
                "The official deterministic probability and confidence are the only "
                "numerical probability/confidence judgments permitted in the official "
                "product. Never mention an AI-adjusted, suggested, alternative, or "
                "recalculated probability/confidence."
            ),
            "grounding": (
                "Use only the official deterministic assessment, deterministic "
                "indicator snapshot, qualitative AI review when supplied, and "
                "canonical_evidence. Do not introduce events, dates, actors, statistics, "
                "or causal claims that are absent from those inputs."
            ),
            "source_attribution": (
                "When discussing a concrete observed development, identify the source "
                "in prose when useful. Do not fabricate citations or URLs."
            ),
            "forecast_format": {
                "near_term_0-30_days": "qualitative trajectory, triggers, and observable conditions",
                "medium_term_31-90_days": "qualitative trajectory, triggers, and observable conditions",
                "longer_term_91-180_days": "qualitative trajectory, triggers, and observable conditions",
            },
            "analytic_structure": [
                "BLUF: official judgment, direction, probability/state, and most important implication",
                "Current evidence: observed developments and corroboration",
                "Assessment: causal drivers, contrary evidence, and why the official score is where it is",
                "Outlook: near-, medium-, and longer-horizon conditions and triggers",
                "Implications: decision-relevant consequences",
                "Collection gaps: what evidence would materially change the judgment",
            ],
            "uncertainty": (
                "Explicitly distinguish observed facts from analytic inference and state "
                "when evidence coverage or source diversity is weak."
            ),
        }
        return context
