from __future__ import annotations

import json
from typing import Any

from app.ai_gateway import AIGatewayRequest, AIResponseFormat, AITaskType
from app.schemas.strategic_intelligence_product import (
    SEWS_OFFICIAL_ASSESSMENT_FORMAT,
    OfficialAssessmentSections,
    ProductGenerationRequest,
    StrategicIntelligenceProduct,
)
from app.services.sews_evidence_context_service import SEWSEvidenceContextService
from app.services.strategic_intelligence_product_service import (
    StrategicIntelligenceProductError,
    StrategicIntelligenceProductService,
)


OA_V2_SYSTEM_PROMPT = """
You are the Official Assessment writing engine for Sovereign Intelligence AI's
Strategic Early Warning System (SEWS).

Your job is to turn an already-issued deterministic SEWS judgment into a clear,
explanatory intelligence assessment for an executive, policy, or business reader.
The deterministic assessment is authoritative. You may explain it, but you must
never alter, replace, recalculate, or compete with its probability, confidence,
severity, warning state, or indicator contributions.

Return VALID JSON ONLY with exactly these top-level keys:
report_format_version
title
report_sections

report_format_version MUST be exactly "SEWS-OA/2.0".

report_sections MUST contain exactly these keys:
key_judgment
why_it_matters
what_is_happening
why_we_assess_this
countervailing_evidence
escalation_pathway
implications
uncertainty_and_gaps
what_to_watch_next
forecast

forecast MUST contain exactly:
near_term_0_30_days
medium_term_31_90_days
longer_term_91_180_days

WRITING STANDARD
- Write for an intelligent reader who does not need to know SEWS terminology.
- Use normal explanatory prose and concrete causal language.
- key_judgment: 1 concise paragraph, normally 3-5 sentences. State the official
  probability and horizon once, then explain what that means in practical terms.
- why_it_matters: explain decision relevance and likely consequences, not model mechanics.
- what_is_happening: explain the observed developments behind the warning. Distinguish
  observations from inference. Cite material evidence claims with [1], [2], etc.
- why_we_assess_this: explain the strongest factors raising or lowering concern in
  human language. Never print raw IND_* identifiers.
- countervailing_evidence: explain what evidence argues against escalation or keeps
  the probability lower. If evidence is weak or stale, say so plainly.
- escalation_pathway: describe a plausible sequence of developments that would move
  the situation toward the defined warning outcome. Do not imply inevitability.
- implications: explain practical consequences for governments, companies, markets,
  infrastructure, communities, or operations as relevant to this warning.
- uncertainty_and_gaps: explain what is unknown, stale, contradictory, thinly sourced,
  or unvalidated, why it matters, and what could change the judgment.
- what_to_watch_next: 3-6 observable, specific developments. These are reader-facing
  warning signs, not raw database indicator names.
- forecast: explain each time band as a trajectory and conditions that would make
  concern rise or fall. Do not invent new numerical probabilities for sub-horizons.

INTERPRETATION STANDARD
- Probability = likelihood that the defined outcome occurs within the forecast horizon.
- Confidence = how strongly the available evidence supports that probability estimate.
- Severity = how consequential the outcome would be if it occurred.
Never treat these as interchangeable scores.

CITATION STANDARD
- canonical_evidence documents include a note_number.
- For each material factual claim drawn from a document, place its note marker at the
  end of the sentence: [1], [2], etc.
- Use only note numbers supplied in canonical_evidence. Never invent a citation.
- Do not put raw URLs in narrative text.
- If the evidence does not support a factual detail, omit the detail.

PROHIBITED
- Raw indicator keys such as IND_*.
- Internal formula language, logits, weights, evidence-balance ratios, or scoring plumbing.
- "AI-adjusted" or alternative probabilities/confidence values.
- A competing AI warning state or recommendation to replace the official state.
- Pseudo-headings embedded inside section prose.
- Generic filler such as "continuous vigilant monitoring will be key."
- Unsupported historical analogs, events, dates, actors, or statistics.
""".strip()


class EvidenceGroundedStrategicIntelligenceProductService(StrategicIntelligenceProductService):
    """Official SEWS product generation grounded in canonical source evidence.

    The legacy product fields remain populated for backward compatibility, but every
    newly generated product is also issued under the structured SEWS-OA/2.0 contract.
    """

    @staticmethod
    def _qualitative_ai_review(ai_review: dict[str, Any] | None) -> dict[str, Any] | None:
        if not ai_review:
            return None
        allowed = {
            "id", "reviewed_at", "model_provider", "model_name", "agreement_score",
            "disposition", "recommended_state", "maintain_official_state", "key_drivers",
            "contrary_evidence", "confidence_rationale", "monitoring_priorities",
            "historical_analogs", "narrative",
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

    def _evidence_context(self, problem_key: str) -> dict[str, Any]:
        return SEWSEvidenceContextService(self.db).build(problem_key, limit=40)

    @staticmethod
    def _evidence_documents(evidence_context: dict[str, Any]) -> list[dict[str, Any]]:
        documents = evidence_context.get("documents") or []
        return [
            {
                "note_number": index + 1,
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
            for index, row in enumerate(documents[:24])
        ]

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
            problem, assessment, self._qualitative_ai_review(ai_review),
            deterministic_drivers, deterministic_contra, request,
        )
        evidence_context = self._evidence_context(str(problem["problem_key"]))
        context["canonical_evidence"] = self._evidence_documents(evidence_context)
        context["evidence_quality"] = evidence_context.get("quality") or {}
        context["reporting_standard"] = {
            "audience": "Write for an intelligent executive or policy reader who may not know SEWS terminology. Teach the reader what the judgment means without requiring technical training.",
            "style": "Use clear explanatory prose, short paragraphs, concrete causal language, and ordinary English. Sound like a senior intelligence analyst briefing a decision-maker, not a model describing its internals.",
            "plain_language": "Never print raw indicator keys such as IND_* in BLUF, executive_summary, full_analysis, forecast, or monitoring priorities. Translate them into human-readable concepts. Define any necessary technical term in plain English on first use.",
            "single_probability_authority": "The official deterministic probability and confidence are the only numerical probability/confidence judgments permitted. Never mention an AI-adjusted, suggested, alternative, or recalculated probability/confidence, and never conclude that the AI review should replace the official state.",
            "probability_explanation": "When giving the official probability, immediately explain what it means for the stated time horizon. Make clear that probability is likelihood, confidence is strength of evidence, and severity is consequence if the event occurs.",
            "confidence_explanation": "Explain confidence using source freshness, corroboration, coverage, and contradictory evidence. Do not quote internal evidence-balance ratios, formula diagnostics, weights, or logits; translate them into practical meaning.",
            "grounding": "Use only the official deterministic assessment, deterministic indicator snapshot, qualitative AI review when supplied, and canonical_evidence. Do not introduce events, dates, actors, statistics, or causal claims absent from those inputs.",
            "chicago_citations": "For every material factual claim based on canonical_evidence, append a bracketed note marker using that document's note_number, for example [1]. Use only note numbers present in canonical_evidence. Do not invent citations. The frontend renders those records as Chicago Notes and Bibliography style references.",
            "uncertainty": "Separate observed facts from analytic inference. Explain uncertainty as a practical limitation: what is not known, why it is not known, and how new evidence could change the judgment.",
        }
        return context

    @staticmethod
    def _compatibility_analysis(sections: OfficialAssessmentSections) -> str:
        parts = [
            sections.what_is_happening,
            sections.why_we_assess_this,
            sections.countervailing_evidence,
            sections.escalation_pathway,
            sections.implications,
            sections.uncertainty_and_gaps,
        ]
        return "\n\n".join(part.strip() for part in parts if part and part.strip())

    def _generate_official_assessment_v2(
        self,
        *,
        problem_key: str,
        legacy_product: StrategicIntelligenceProduct,
        request: ProductGenerationRequest,
    ) -> tuple[str, OfficialAssessmentSections, dict[str, Any]]:
        evidence_context = self._evidence_context(problem_key)
        canonical_evidence = self._evidence_documents(evidence_context)
        official = legacy_product.official_assessment

        v2_context = {
            "report_format_version": SEWS_OFFICIAL_ASSESSMENT_FORMAT,
            "warning_problem": {
                "problem_key": problem_key,
                "title": legacy_product.title,
            },
            "official_deterministic_assessment": official,
            "deterministic_drivers": legacy_product.drivers,
            "deterministic_contrary_evidence": legacy_product.contrary_evidence,
            "qualitative_ai_review": self._qualitative_ai_review(legacy_product.ai_strategic_review),
            "evidence_quality": evidence_context.get("quality") or {},
            "canonical_evidence": canonical_evidence,
            "legacy_narrative_for_context_only": {
                "bluf": legacy_product.bluf,
                "executive_summary": legacy_product.executive_summary,
                "full_analysis": legacy_product.full_analysis,
            },
        }

        response = self.gateway.generate(
            AIGatewayRequest(
                task_type=AITaskType.FULL_ANALYSIS,
                system_prompt=OA_V2_SYSTEM_PROMPT,
                user_prompt=json.dumps(v2_context, ensure_ascii=False, default=str),
                preferred_provider=request.preferred_provider,
                preferred_model=request.preferred_model,
                response_format=AIResponseFormat.JSON,
                temperature=0.15,
                metadata={
                    "problem_key": problem_key,
                    "assessment_id": str(request.assessment_id),
                    "product_type": request.product_type,
                    "report_format_version": SEWS_OFFICIAL_ASSESSMENT_FORMAT,
                },
            )
        )
        raw = (
            response.parsed_json
            if isinstance(response.parsed_json, dict)
            else json.loads(response.content)
        )
        if raw.get("report_format_version") != SEWS_OFFICIAL_ASSESSMENT_FORMAT:
            raise StrategicIntelligenceProductError("Official Assessment output did not declare SEWS-OA/2.0.")
        if not isinstance(raw.get("report_sections"), dict):
            raise StrategicIntelligenceProductError("Official Assessment output is missing report_sections.")

        try:
            sections = OfficialAssessmentSections.model_validate(raw["report_sections"])
        except Exception as exc:
            raise StrategicIntelligenceProductError(
                f"Official Assessment failed SEWS-OA/2.0 section validation: {exc}"
            ) from exc

        public_text = "\n".join([
            sections.key_judgment,
            sections.why_it_matters,
            sections.what_is_happening,
            sections.why_we_assess_this,
            sections.countervailing_evidence,
            sections.escalation_pathway,
            sections.implications,
            sections.uncertainty_and_gaps,
            *sections.what_to_watch_next,
            sections.forecast.near_term_0_30_days,
            sections.forecast.medium_term_31_90_days,
            sections.forecast.longer_term_91_180_days,
        ])
        if "IND_" in public_text.upper():
            raise StrategicIntelligenceProductError("Official Assessment contains raw indicator identifiers.")
        if not sections.key_judgment.strip() or not sections.what_is_happening.strip():
            raise StrategicIntelligenceProductError("Official Assessment is missing core reader-facing sections.")
        if len(sections.what_to_watch_next) < 3:
            raise StrategicIntelligenceProductError("Official Assessment requires at least three observable watch items.")

        title = str(raw.get("title") or legacy_product.title).strip()
        generation_meta = {
            "ai_provider": response.provider,
            "ai_model": response.model,
            "ai_latency_ms": response.latency_ms,
            "ai_usage": response.usage,
            "canonical_evidence_count": len(canonical_evidence),
        }
        return title, sections, generation_meta

    def generate(
        self,
        problem_key: str,
        request: ProductGenerationRequest,
    ) -> StrategicIntelligenceProduct:
        # Preserve the proven deterministic + persistence pipeline, then issue the
        # reader-facing OA/2.0 document from exactly that authoritative product.
        legacy_product = super().generate(problem_key, request)
        title, sections, v2_meta = self._generate_official_assessment_v2(
            problem_key=problem_key,
            legacy_product=legacy_product,
            request=request,
        )

        section_payload = sections.model_dump(mode="json")
        publication = dict(legacy_product.publication or {})
        publication.update({
            "report_format_version": SEWS_OFFICIAL_ASSESSMENT_FORMAT,
            "report_sections": section_payload,
        })

        forecast = {
            "near_term_0-30_days": sections.forecast.near_term_0_30_days,
            "medium_term_31-90_days": sections.forecast.medium_term_31_90_days,
            "longer_term_91-180_days": sections.forecast.longer_term_91_180_days,
        }
        full_analysis = self._compatibility_analysis(sections)
        qa = dict(legacy_product.quality_assurance or {})
        checks = dict(qa.get("checks") or {})
        checks.update({
            "official_assessment_v2": True,
            "structured_sections_present": True,
            "raw_indicator_ids_absent_from_public_report": True,
            "reader_watch_items_present": len(sections.what_to_watch_next) >= 3,
        })
        qa["checks"] = checks
        qa["report_format_version"] = SEWS_OFFICIAL_ASSESSMENT_FORMAT
        qa["passed"] = all(bool(value) for value in checks.values())

        provenance = dict(legacy_product.confidence_and_provenance or {})
        provenance["official_assessment_v2_generation"] = v2_meta

        update_row = {
            "title": title,
            "bluf": sections.key_judgment,
            "executive_summary": sections.why_it_matters,
            "monitoring_priorities": sections.what_to_watch_next,
            "forecast": forecast,
            "full_analysis": full_analysis,
            "quality_assurance": qa,
            "publication": publication,
            "confidence_and_provenance": provenance,
        }
        result = (
            self.db.table("strategic_intelligence_products")
            .update(update_row)
            .eq("product_key", legacy_product.product_key)
            .execute()
        )
        if not result.data:
            raise StrategicIntelligenceProductError("SEWS-OA/2.0 persistence returned no product row.")

        if request.publish_to_ledger:
            existing_ledger = (
                self.db.table("sews_warning_ledger")
                .select("id,narrative_body")
                .eq("assessment_id", str(request.assessment_id))
                .limit(1)
                .execute()
            )
            if existing_ledger.data:
                ledger_body = dict(existing_ledger.data[0].get("narrative_body") or {})
                ledger_body.update({
                    "report_format_version": SEWS_OFFICIAL_ASSESSMENT_FORMAT,
                    "report_sections": section_payload,
                    "bluf": sections.key_judgment,
                    "executive_summary": sections.why_it_matters,
                    "monitoring_priorities": sections.what_to_watch_next,
                    "forecast": forecast,
                    "full_analysis": full_analysis,
                })
                self.db.table("sews_warning_ledger").update({
                    "narrative_body": ledger_body,
                }).eq("id", existing_ledger.data[0]["id"]).execute()

        return StrategicIntelligenceProduct(
            product_id=legacy_product.product_id,
            product_key=legacy_product.product_key,
            product_type=legacy_product.product_type,
            problem_key=legacy_product.problem_key,
            assessment_id=legacy_product.assessment_id,
            ai_review_id=legacy_product.ai_review_id,
            report_format_version=SEWS_OFFICIAL_ASSESSMENT_FORMAT,
            report_sections=sections,
            title=title,
            bluf=sections.key_judgment,
            executive_summary=sections.why_it_matters,
            official_assessment=legacy_product.official_assessment,
            ai_strategic_review=legacy_product.ai_strategic_review,
            drivers=legacy_product.drivers,
            contrary_evidence=legacy_product.contrary_evidence,
            confidence_and_provenance=provenance,
            historical_analogs=legacy_product.historical_analogs,
            monitoring_priorities=sections.what_to_watch_next,
            forecast=forecast,
            full_analysis=full_analysis,
            quality_assurance=qa,
            publication=publication,
            created_at=legacy_product.created_at,
            published_at=legacy_product.published_at,
        )
