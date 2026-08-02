from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from supabase import Client

from app.ai_gateway import (
    AIGatewayRequest,
    AIResponseFormat,
    AITaskType,
    get_ai_gateway,
)
from app.schemas.strategic_intelligence_product import (
    ProductGenerationRequest,
    StrategicIntelligenceProduct,
)


class StrategicIntelligenceProductError(RuntimeError):
    pass


SYSTEM_PROMPT = """
You are the Strategic Intelligence Production Engine for Sovereign Intelligence AI.

You receive an official deterministic assessment and, when available, an independent
AI strategic review. The deterministic assessment is authoritative. Never alter,
recalculate, or replace its probability, confidence, severity, state, indicator
contributions, formula version, or evidence counts.

Return valid JSON only, with exactly these keys:
bluf
executive_summary
drivers
contrary_evidence
historical_analogs
monitoring_priorities
forecast
full_analysis

Requirements:
- BLUF must be one paragraph and no more than seven sentences.
- full_analysis should be approximately 500 words.
- drivers must be evidence-based and linked to indicator keys.
- contrary_evidence must explicitly identify evidence against escalation.
- monitoring_priorities must be observable and specific.
- forecast must distinguish near-, medium-, and longer-term horizons.
- Do not invent evidence, sources, dates, or historical analogs.
- If historical analog evidence is unavailable, return an empty list.
- Clearly distinguish official deterministic judgment from AI review.
""".strip()


class StrategicIntelligenceProductService:
    def __init__(self, db: Client):
        self.db = db
        self.gateway = get_ai_gateway()

    def _problem_and_assessment(
        self,
        problem_key: str,
        assessment_id: UUID,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        problem_result = (
            self.db.table("sews_warning_problems")
            .select(
                "id,problem_key,title,hypothesis,horizon_days,state,"
                "severity_score,version"
            )
            .eq("problem_key", problem_key)
            .limit(1)
            .execute()
        )
        if not problem_result.data:
            raise StrategicIntelligenceProductError(
                f"Unknown warning problem: {problem_key}"
            )
        problem = problem_result.data[0]

        assessment_result = (
            self.db.table("sews_assessments")
            .select("*")
            .eq("id", str(assessment_id))
            .eq("warning_problem_id", problem["id"])
            .limit(1)
            .execute()
        )
        if not assessment_result.data:
            raise StrategicIntelligenceProductError(
                "Assessment not found for this warning problem."
            )

        return problem, assessment_result.data[0]

    def _ai_review(
        self,
        *,
        problem_id: str,
        assessment_id: UUID,
        ai_review_id: UUID | None,
    ) -> dict[str, Any] | None:
        query = (
            self.db.table("sews_ai_reviews")
            .select("*")
            .eq("warning_problem_id", problem_id)
            .eq("assessment_id", str(assessment_id))
        )

        if ai_review_id is not None:
            query = query.eq("id", str(ai_review_id))

        result = query.order("reviewed_at", desc=True).limit(1).execute()
        return result.data[0] if result.data else None

    @staticmethod
    def _sentence_count(text: str) -> int:
        return len(
            [
                item
                for item in re.split(r"(?<=[.!?])\s+", text.strip())
                if item.strip()
            ]
        )

    @staticmethod
    def _word_count(text: str) -> int:
        return len(re.findall(r"\b[\w'-]+\b", text))

    @staticmethod
    def _context_payload(
        problem: dict[str, Any],
        assessment: dict[str, Any],
        ai_review: dict[str, Any] | None,
        deterministic_drivers: list[dict[str, Any]],
        deterministic_contra: list[dict[str, Any]],
        request: ProductGenerationRequest,
    ) -> dict[str, Any]:
        return {
            "warning_problem": {
                "problem_key": problem["problem_key"],
                "title": problem["title"],
                "hypothesis": problem["hypothesis"],
                "horizon_days": problem["horizon_days"],
                "current_state": problem["state"],
            },
            "official_assessment": {
                "probability": assessment["probability"],
                "probability_band": assessment["probability_band"],
                "confidence_score": assessment["confidence_score"],
                "confidence_level": assessment["confidence_level"],
                "severity_score": assessment["severity_score"],
                "recommended_state": assessment["recommended_state"],
                "confidence_breakdown": assessment[
                    "confidence_breakdown"
                ],
                "formula_version": assessment["formula_version"],
                "deterministic_payload": assessment[
                    "deterministic_payload"
                ],
            },
            "deterministic_drivers": deterministic_drivers[:12],
            "deterministic_contrary_evidence": deterministic_contra[:12],
            "ai_strategic_review": ai_review,
            "audience": request.audience,
            "product_type": request.product_type,
        }

    @staticmethod
    def _validate_model_payload(payload: dict[str, Any]) -> dict[str, Any]:
        payload = dict(payload or {})

        for key in (
            "drivers",
            "contrary_evidence",
            "historical_analogs",
            "monitoring_priorities",
        ):
            if payload.get(key) is None:
                payload[key] = []

        if payload.get("forecast") is None:
            payload["forecast"] = {}

        priorities = payload.get("monitoring_priorities") or []
        normalized_priorities = []

        for item in priorities:
            if isinstance(item, str):
                normalized_priorities.append(item.strip())
            elif isinstance(item, dict):
                value = (
                    item.get("priority")
                    or item.get("title")
                    or item.get("name")
                    or item.get("action")
                    or item.get("description")
                )
                if value:
                    normalized_priorities.append(str(value).strip())
            elif item is not None:
                normalized_priorities.append(str(item).strip())

        payload["monitoring_priorities"] = normalized_priorities

        for key in (
            "bluf",
            "executive_summary",
            "full_analysis",
        ):
            value = payload.get(key)

            if value is None:
                payload[key] = ""
            elif isinstance(value, str):
                payload[key] = value.strip()
            elif isinstance(value, dict):
                extracted = (
                    value.get("text")
                    or value.get("content")
                    or value.get("summary")
                    or value.get("analysis")
                    or value.get("narrative")
                    or ""
                )
                payload[key] = str(extracted).strip()
            elif isinstance(value, list):
                payload[key] = "\n\n".join(
                    str(item).strip()
                    for item in value
                    if item is not None
                )
            else:
                payload[key] = str(value).strip()

        required = {
            "bluf",
            "executive_summary",
            "drivers",
            "contrary_evidence",
            "historical_analogs",
            "monitoring_priorities",
            "forecast",
            "full_analysis",
        }
        missing = required - payload.keys()
        if missing:
            raise StrategicIntelligenceProductError(
                f"Product output missing keys: {sorted(missing)}"
            )

        if not isinstance(payload["drivers"], list):
            raise StrategicIntelligenceProductError(
                "drivers must be a list."
            )
        if not isinstance(payload["contrary_evidence"], list):
            raise StrategicIntelligenceProductError(
                "contrary_evidence must be a list."
            )
        if not isinstance(payload["monitoring_priorities"], list):
            raise StrategicIntelligenceProductError(
                "monitoring_priorities must be a list."
            )
        if not isinstance(payload["forecast"], dict):
            raise StrategicIntelligenceProductError(
                "forecast must be an object."
            )

        return payload

    def _qa(
        self,
        *,
        model_payload: dict[str, Any],
        assessment: dict[str, Any],
        deterministic_drivers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        bluf_sentences = self._sentence_count(model_payload["bluf"])
        analysis_words = self._word_count(model_payload["full_analysis"])

        checks = {
            "official_probability_present": (
                assessment.get("probability") is not None
            ),
            "official_confidence_present": (
                assessment.get("confidence_score") is not None
            ),
            "official_severity_present": (
                assessment.get("severity_score") is not None
            ),
            "official_state_present": (
                assessment.get("recommended_state") is not None
            ),
            "bluf_sentence_limit": bluf_sentences <= 7,
            "analysis_word_range": 500 <= analysis_words <= 700,
            "drivers_present": bool(deterministic_drivers),
            "contrary_evidence_section_present": (
                "contrary_evidence" in model_payload
            ),
            "forecast_present": bool(model_payload["forecast"]),
            "monitoring_priorities_present": bool(
                model_payload["monitoring_priorities"]
            ),
        }

        return {
            "passed": all(checks.values()),
            "checks": checks,
            "metrics": {
                "bluf_sentence_count": bluf_sentences,
                "analysis_word_count": analysis_words,
            },
        }

    @staticmethod
    def _product_key(
        problem_key: str,
        assessment_id: UUID,
        product_type: str,
    ) -> str:
        raw = f"{problem_key}|{assessment_id}|{product_type}"
        digest = hashlib.sha256(raw.encode()).hexdigest()[:20]
        return f"SIP-{problem_key}-{digest}".upper()


    @staticmethod
    def _indicator_drivers(
        assessment: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        snapshot = assessment.get("indicator_snapshot") or []

        ordered = sorted(
            snapshot,
            key=lambda item: abs(float(item.get("weighted_contribution") or 0)),
            reverse=True,
        )

        drivers = []
        contra = []

        for item in ordered:
            record = {
                "indicator_key": item.get("indicator_key"),
                "indicator_class": item.get("indicator_class"),
                "current_value": item.get("current_value"),
                "confidence": item.get("confidence"),
                "weighted_contribution": item.get("weighted_contribution"),
                "status": item.get("status"),
            }

            if str(item.get("status", "")).upper() == "ACTIVE":
                drivers.append(record)

            if (
                str(item.get("indicator_class", "")).upper() == "CONTRA"
                or str(item.get("polarity", "")).upper() == "CONTRADICTING"
            ):
                contra.append(record)

        return drivers, contra

    def generate(
        self,
        problem_key: str,
        request: ProductGenerationRequest,
    ) -> StrategicIntelligenceProduct:
        problem, assessment = self._problem_and_assessment(
            problem_key,
            request.assessment_id,
        )
        ai_review = self._ai_review(
            problem_id=problem["id"],
            assessment_id=request.assessment_id,
            ai_review_id=request.ai_review_id,
        )

        deterministic_drivers, deterministic_contra = (
            self._indicator_drivers(assessment)
        )

        context = self._context_payload(
            problem,
            assessment,
            ai_review,
            deterministic_drivers,
            deterministic_contra,
            request,
        )

        response = self.gateway.generate(
            AIGatewayRequest(
                task_type=AITaskType.FULL_ANALYSIS,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=json.dumps(
                    context,
                    ensure_ascii=False,
                    default=str,
                ),
                preferred_provider=request.preferred_provider,
                preferred_model=request.preferred_model,
                response_format=AIResponseFormat.JSON,
                temperature=0.2,
                metadata={
                    "problem_key": problem_key,
                    "assessment_id": str(request.assessment_id),
                    "product_type": request.product_type,
                },
            )
        )

        payload = self._validate_model_payload(
            response.parsed_json
            if isinstance(response.parsed_json, dict)
            else json.loads(response.content)
        )

        max_attempts = 3

        for attempt in range(max_attempts):
            qa = self._qa(
                model_payload=payload,
                assessment=assessment,
                deterministic_drivers=deterministic_drivers,
            )

            if qa["passed"]:
                break

            only_short_report = (
                not qa["checks"]["analysis_word_range"]
                and all(
                    value
                    for key, value in qa["checks"].items()
                    if key != "analysis_word_range"
                )
            )

            if not only_short_report or attempt == max_attempts - 1:
                raise StrategicIntelligenceProductError(
                    f"Product failed quality assurance: {qa}"
                )

            response = self.gateway.generate(
                AIGatewayRequest(
                    task_type=AITaskType.FULL_ANALYSIS,
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=(
                        json.dumps(
                            context,
                            ensure_ascii=False,
                            default=str,
                        )
                        + "\n\nPREVIOUS PRODUCT:\n"
                        + json.dumps(
                            payload,
                            ensure_ascii=False,
                            default=str,
                        )
                        + (
                            f"\n\nThe previous full_analysis contains "
                            f"{self._word_count(payload['full_analysis'])} words. "
                            "Return the complete valid JSON product again with every "
                            "required key. Expand only the full_analysis to 575–650 "
                            "words by adding evidence-grounded explanation of drivers, "
                            "contrary evidence, escalation pathways, implications, and "
                            "monitoring priorities. Do not summarize or shorten it. "
                            "Preserve the official deterministic probability, confidence, "
                            "severity, state, drivers, and evidence exactly."
                        )
                    ),
                    preferred_provider=request.preferred_provider,
                    preferred_model=request.preferred_model,
                    response_format=AIResponseFormat.JSON,
                    temperature=0.2,
                    metadata={
                        "problem_key": problem_key,
                        "assessment_id": str(request.assessment_id),
                        "product_type": request.product_type,
                    },
                )
            )

            payload = self._validate_model_payload(
                response.parsed_json
                if isinstance(response.parsed_json, dict)
                else json.loads(response.content)
            )

        created_at = datetime.now(timezone.utc)
        product_key = self._product_key(
            problem_key,
            request.assessment_id,
            request.product_type,
        )

        provenance = {
            "formula_version": assessment["formula_version"],
            "assessment_id": str(request.assessment_id),
            "ai_review_id": (
                str(ai_review["id"]) if ai_review else None
            ),
            "ai_provider": response.provider,
            "ai_model": response.model,
            "ai_latency_ms": response.latency_ms,
            "ai_usage": response.usage,
            "indicator_count": len(
                assessment.get("indicator_snapshot") or []
            ),
            "confidence_breakdown": assessment[
                "confidence_breakdown"
            ],
            "deterministic_payload": assessment[
                "deterministic_payload"
            ],
        }

        official_assessment = {
            "probability": assessment["probability"],
            "probability_band": assessment["probability_band"],
            "confidence_score": assessment["confidence_score"],
            "confidence_level": assessment["confidence_level"],
            "severity_score": assessment["severity_score"],
            "recommended_state": assessment["recommended_state"],
            "assessed_at": assessment["assessed_at"],
        }

        publication = {
            "status": "PUBLISHED" if request.publish_product else "DRAFT",
            "ledger_requested": request.publish_to_ledger,
            "audience": request.audience,
        }

        row = {
            "product_key": product_key,
            "product_type": request.product_type,
            "warning_problem_id": problem["id"],
            "assessment_id": str(request.assessment_id),
            "ai_review_id": ai_review["id"] if ai_review else None,
            "title": problem["title"],
            "bluf": payload["bluf"],
            "executive_summary": payload["executive_summary"],
            "official_assessment": official_assessment,
            "ai_strategic_review": ai_review,
            "drivers": deterministic_drivers,
            "contrary_evidence": deterministic_contra,
            "confidence_and_provenance": provenance,
            "historical_analogs": payload["historical_analogs"],
            "monitoring_priorities": payload[
                "monitoring_priorities"
            ],
            "forecast": payload["forecast"],
            "full_analysis": payload["full_analysis"],
            "quality_assurance": qa,
            "publication": publication,
            "published_at": (
                created_at.isoformat()
                if request.publish_product
                else None
            ),
            "created_at": created_at.isoformat(),
            "updated_at": created_at.isoformat(),
        }

        result = (
            self.db.table("strategic_intelligence_products")
            .upsert(row, on_conflict="product_key")
            .execute()
        )
        if not result.data:
            raise StrategicIntelligenceProductError(
                "Product persistence returned no row."
            )

        saved = result.data[0]

        if request.publish_to_ledger:
            ledger_body = {
                "product_key": product_key,
                "bluf": payload["bluf"],
                "executive_summary": payload["executive_summary"],
                "full_analysis": payload["full_analysis"],
                "drivers": deterministic_drivers,
                "contrary_evidence": deterministic_contra,
                "historical_analogs": payload[
                    "historical_analogs"
                ],
                "monitoring_priorities": payload[
                    "monitoring_priorities"
                ],
                "forecast": payload["forecast"],
                "quality_assurance": qa,
                "confidence_and_provenance": provenance,
            }

            existing_ledger = (
                self.db.table("sews_warning_ledger")
                .select("id")
                .eq("assessment_id", str(request.assessment_id))
                .limit(1)
                .execute()
            )

            if existing_ledger.data:
                self.db.table("sews_warning_ledger").update(
                    {
                        "narrative_body": ledger_body,
                        "published_at": (
                            created_at.isoformat()
                            if request.publish_product
                            else None
                        ),
                    }
                ).eq("id", existing_ledger.data[0]["id"]).execute()

        return StrategicIntelligenceProduct(
            product_id=saved["id"],
            product_key=product_key,
            product_type=request.product_type,
            problem_key=problem_key,
            assessment_id=request.assessment_id,
            ai_review_id=(
                UUID(str(ai_review["id"])) if ai_review else None
            ),
            title=problem["title"],
            bluf=payload["bluf"],
            executive_summary=payload["executive_summary"],
            official_assessment=official_assessment,
            ai_strategic_review=ai_review,
            drivers=deterministic_drivers,
            contrary_evidence=deterministic_contra,
            confidence_and_provenance=provenance,
            historical_analogs=payload["historical_analogs"],
            monitoring_priorities=payload[
                "monitoring_priorities"
            ],
            forecast=payload["forecast"],
            full_analysis=payload["full_analysis"],
            quality_assurance=qa,
            publication=publication,
            created_at=saved["created_at"],
            published_at=saved.get("published_at"),
        )

    def history(
        self,
        problem_key: str,
        *,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        problem_result = (
            self.db.table("sews_warning_problems")
            .select("id")
            .eq("problem_key", problem_key)
            .limit(1)
            .execute()
        )
        if not problem_result.data:
            raise StrategicIntelligenceProductError(
                f"Unknown warning problem: {problem_key}"
            )

        result = (
            self.db.table("strategic_intelligence_products")
            .select("*")
            .eq(
                "warning_problem_id",
                problem_result.data[0]["id"],
            )
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
