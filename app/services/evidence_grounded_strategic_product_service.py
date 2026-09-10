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
            ai_review,
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
            "grounding": (
                "Use only the official deterministic assessment, deterministic "
                "indicator snapshot, AI review when supplied, and canonical_evidence. "
                "Do not introduce events, dates, actors, statistics, or causal claims "
                "that are absent from those inputs."
            ),
            "source_attribution": (
                "When discussing a concrete observed development, identify the source "
                "in prose when useful. Do not fabricate citations or URLs."
            ),
            "analytic_structure": [
                "BLUF: judgment, direction, probability/state, and most important implication",
                "Current evidence: observed developments and corroboration",
                "Assessment: causal drivers, contrary evidence, and why the score is where it is",
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
