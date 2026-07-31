from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from openai import OpenAI
from supabase import Client

from app.schemas.sews_ai_review import (
    AIReviewRequest,
    AIReviewResponse,
    AssessmentComparisonResponse,
    ReviewDisposition,
)


class SEWSAIReviewError(RuntimeError):
    pass


SYSTEM_PROMPT = """
You are the independent strategic review layer for a professional strategic
early warning system.

The deterministic assessment is the official assessment and must remain
unchanged. Your role is to review it, challenge it, and return an independent
second opinion.

Return JSON only. Do not include markdown.

Rules:
1. Do not repeat the official assessment as your own without analysis.
2. Suggested probability and confidence must each be between 0 and 1.
3. recommended_state must be one of:
   DORMANT, WATCH, ADVISORY, WARNING, CRITICAL, RESOLVED, FALSIFIED.
4. key_drivers must contain the strongest supporting considerations.
5. contrary_evidence must contain the strongest evidence against escalation.
6. monitoring_priorities must be specific observable developments.
7. historical_analogs must be objects with:
   name, similarity, lesson.
8. narrative must explain the review in no more than 350 words.
9. The output must be valid JSON with exactly these keys:
   suggested_probability
   suggested_confidence
   recommended_state
   key_drivers
   contrary_evidence
   confidence_rationale
   monitoring_priorities
   historical_analogs
   narrative
""".strip()


class SEWSAIReviewService:
    def __init__(self, db: Client):
        self.db = db

    def _assessment(
        self,
        problem_key: str,
        assessment_id: UUID,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        problem_result = (
            self.db.table("sews_warning_problems")
            .select(
                "id,problem_key,title,hypothesis,horizon_days,state,"
                "severity_score,transition_rules"
            )
            .eq("problem_key", problem_key)
            .limit(1)
            .execute()
        )
        if not problem_result.data:
            raise SEWSAIReviewError(
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
            raise SEWSAIReviewError(
                "Assessment not found for this warning problem."
            )
        return problem, assessment_result.data[0]

    @staticmethod
    def _disposition(variance: float) -> ReviewDisposition:
        absolute = abs(variance)
        if absolute <= 0.05:
            return ReviewDisposition.AGREE
        if absolute <= 0.10:
            return ReviewDisposition.MINOR_DISAGREEMENT
        if absolute <= 0.20:
            return ReviewDisposition.MAJOR_DISAGREEMENT
        return ReviewDisposition.CRITICAL_DIVERGENCE

    @staticmethod
    def _agreement_score(variance: float) -> float:
        return round(max(0.0, 1.0 - abs(variance)), 4)

    @staticmethod
    def _client(
        provider: str,
        model_name: str | None,
    ) -> tuple[OpenAI, str]:
        normalized = provider.strip().upper()

        if normalized == "NVIDIA":
            api_key = os.getenv("NVIDIA_API_KEY")
            base_url = os.getenv(
                "NVIDIA_BASE_URL",
                "https://integrate.api.nvidia.com/v1",
            )
            model = (
                model_name
                or os.getenv(
                    "NVIDIA_NEMOTRON_MODEL",
                    "nvidia/llama-3.3-nemotron-super-49b-v1",
                )
            )
        elif normalized == "OPENAI":
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv(
                "OPENAI_BASE_URL",
                "https://api.openai.com/v1",
            )
            model = model_name or os.getenv(
                "OPENAI_REVIEW_MODEL",
                "gpt-5-mini",
            )
        else:
            raise SEWSAIReviewError(
                f"Unsupported review provider: {provider}"
            )

        if not api_key:
            raise SEWSAIReviewError(
                f"Missing API key for provider {normalized}."
            )

        return OpenAI(api_key=api_key, base_url=base_url), model

    @staticmethod
    def _prompt(
        problem: dict[str, Any],
        assessment: dict[str, Any],
        request: AIReviewRequest,
    ) -> str:
        payload = {
            "warning_problem": {
                "problem_key": problem["problem_key"],
                "title": problem["title"],
                "hypothesis": problem["hypothesis"],
                "horizon_days": problem["horizon_days"],
                "current_state": problem["state"],
                "severity_score": problem["severity_score"],
            },
            "official_assessment": {
                "probability": assessment["probability"],
                "probability_band": assessment["probability_band"],
                "confidence_score": assessment["confidence_score"],
                "confidence_level": assessment["confidence_level"],
                "severity_score": assessment["severity_score"],
                "recommended_state": assessment["recommended_state"],
                "indicator_snapshot": assessment["indicator_snapshot"],
                "confidence_breakdown": assessment["confidence_breakdown"],
                "formula_version": assessment["formula_version"],
                "deterministic_payload": assessment[
                    "deterministic_payload"
                ],
            },
            "review_options": {
                "include_historical_analogs": (
                    request.include_historical_analogs
                ),
                "include_monitoring_priorities": (
                    request.include_monitoring_priorities
                ),
            },
        }

        return (
            "Review the following official deterministic SEWS assessment.\n"
            "Return the required JSON object only.\n\n"
            + json.dumps(payload, ensure_ascii=False, default=str)
        )

    @staticmethod
    def _parse_json(content: str) -> dict[str, Any]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise SEWSAIReviewError(
                "The AI review did not return valid JSON."
            ) from exc

    @staticmethod
    def _validate_review(
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        required = {
            "suggested_probability",
            "suggested_confidence",
            "recommended_state",
            "key_drivers",
            "contrary_evidence",
            "confidence_rationale",
            "monitoring_priorities",
            "historical_analogs",
            "narrative",
        }
        missing = required - payload.keys()
        if missing:
            raise SEWSAIReviewError(
                f"AI review missing keys: {sorted(missing)}"
            )

        probability = float(payload["suggested_probability"])
        confidence = float(payload["suggested_confidence"])
        if not 0 <= probability <= 1:
            raise SEWSAIReviewError(
                "suggested_probability must be between 0 and 1."
            )
        if not 0 <= confidence <= 1:
            raise SEWSAIReviewError(
                "suggested_confidence must be between 0 and 1."
            )

        allowed_states = {
            "DORMANT",
            "WATCH",
            "ADVISORY",
            "WARNING",
            "CRITICAL",
            "RESOLVED",
            "FALSIFIED",
        }
        state = str(payload["recommended_state"]).upper()
        if state not in allowed_states:
            raise SEWSAIReviewError(
                f"Invalid AI-recommended state: {state}"
            )

        payload["suggested_probability"] = probability
        payload["suggested_confidence"] = confidence
        payload["recommended_state"] = state
        payload["key_drivers"] = [
            str(item) for item in payload["key_drivers"]
        ]
        payload["contrary_evidence"] = [
            str(item) for item in payload["contrary_evidence"]
        ]
        payload["monitoring_priorities"] = [
            str(item) for item in payload["monitoring_priorities"]
        ]
        return payload

    def review(
        self,
        problem_key: str,
        request: AIReviewRequest,
    ) -> AIReviewResponse:
        problem, assessment = self._assessment(
            problem_key,
            request.assessment_id,
        )

        client, model = self._client(
            request.model_provider,
            request.model_name,
        )

        response = client.chat.completions.create(
            model=model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": self._prompt(
                        problem,
                        assessment,
                        request,
                    ),
                },
            ],
        )

        content = response.choices[0].message.content or ""
        raw_review = self._validate_review(
            self._parse_json(content)
        )

        official_probability = float(assessment["probability"])
        official_confidence = (
            float(assessment["confidence_score"]) / 100.0
        )
        probability_variance = round(
            raw_review["suggested_probability"]
            - official_probability,
            4,
        )
        confidence_variance = round(
            raw_review["suggested_confidence"]
            - official_confidence,
            4,
        )
        disposition = self._disposition(probability_variance)
        agreement_score = self._agreement_score(
            probability_variance
        )
        reviewed_at = datetime.now(timezone.utc)

        row = {
            "warning_problem_id": problem["id"],
            "assessment_id": str(request.assessment_id),
            "reviewed_at": reviewed_at.isoformat(),
            "model_provider": request.model_provider.upper(),
            "model_name": model,
            "official_probability": official_probability,
            "official_confidence": official_confidence,
            "suggested_probability": raw_review[
                "suggested_probability"
            ],
            "suggested_confidence": raw_review[
                "suggested_confidence"
            ],
            "probability_variance": probability_variance,
            "confidence_variance": confidence_variance,
            "agreement_score": agreement_score,
            "disposition": disposition.value,
            "recommended_state": raw_review[
                "recommended_state"
            ],
            "maintain_official_state": (
                raw_review["recommended_state"]
                == assessment["recommended_state"]
            ),
            "key_drivers": raw_review["key_drivers"],
            "contrary_evidence": raw_review[
                "contrary_evidence"
            ],
            "confidence_rationale": raw_review[
                "confidence_rationale"
            ],
            "monitoring_priorities": raw_review[
                "monitoring_priorities"
            ],
            "historical_analogs": raw_review[
                "historical_analogs"
            ],
            "narrative": raw_review["narrative"],
            "raw_model_output": raw_review,
        }

        review_id = None
        persisted = False

        if request.persist:
            existing = (
                self.db.table("sews_ai_reviews")
                .select("id")
                .eq("assessment_id", str(request.assessment_id))
                .eq("model_provider", request.model_provider.upper())
                .eq("model_name", model)
                .limit(1)
                .execute()
            )

            if existing.data:
                result = (
                    self.db.table("sews_ai_reviews")
                    .update(row)
                    .eq("id", existing.data[0]["id"])
                    .execute()
                )
            else:
                result = (
                    self.db.table("sews_ai_reviews")
                    .insert(row)
                    .execute()
                )

            if not result.data:
                raise SEWSAIReviewError(
                    "AI review persistence returned no row."
                )
            review_id = result.data[0]["id"]
            persisted = True

        return AIReviewResponse(
            id=review_id,
            problem_key=problem_key,
            assessment_id=request.assessment_id,
            reviewed_at=reviewed_at,
            model_provider=request.model_provider.upper(),
            model_name=model,
            official_probability=official_probability,
            official_confidence=official_confidence,
            suggested_probability=raw_review[
                "suggested_probability"
            ],
            suggested_confidence=raw_review[
                "suggested_confidence"
            ],
            probability_variance=probability_variance,
            confidence_variance=confidence_variance,
            agreement_score=agreement_score,
            disposition=disposition,
            recommended_state=raw_review["recommended_state"],
            maintain_official_state=(
                raw_review["recommended_state"]
                == assessment["recommended_state"]
            ),
            key_drivers=raw_review["key_drivers"],
            contrary_evidence=raw_review["contrary_evidence"],
            confidence_rationale=raw_review[
                "confidence_rationale"
            ],
            monitoring_priorities=raw_review[
                "monitoring_priorities"
            ],
            historical_analogs=raw_review[
                "historical_analogs"
            ],
            narrative=raw_review["narrative"],
            raw_model_output=raw_review,
            persisted=persisted,
        )

    def comparison(
        self,
        problem_key: str,
        *,
        assessment_id: UUID,
        review_id: UUID,
    ) -> AssessmentComparisonResponse:
        problem, assessment = self._assessment(
            problem_key,
            assessment_id,
        )
        review_result = (
            self.db.table("sews_ai_reviews")
            .select("*")
            .eq("id", str(review_id))
            .eq("assessment_id", str(assessment_id))
            .eq("warning_problem_id", problem["id"])
            .limit(1)
            .execute()
        )
        if not review_result.data:
            raise SEWSAIReviewError(
                "AI review not found for this assessment."
            )
        review = review_result.data[0]
        disposition = ReviewDisposition(review["disposition"])

        return AssessmentComparisonResponse(
            problem_key=problem_key,
            assessment_id=assessment_id,
            review_id=review_id,
            official={
                "probability": assessment["probability"],
                "confidence_score": assessment[
                    "confidence_score"
                ],
                "severity_score": assessment["severity_score"],
                "state": assessment["recommended_state"],
                "formula_version": assessment["formula_version"],
            },
            ai_review={
                "suggested_probability": review[
                    "suggested_probability"
                ],
                "suggested_confidence": review[
                    "suggested_confidence"
                ],
                "recommended_state": review[
                    "recommended_state"
                ],
                "agreement_score": review["agreement_score"],
                "model_provider": review["model_provider"],
                "model_name": review["model_name"],
            },
            variance={
                "probability": review["probability_variance"],
                "confidence": review["confidence_variance"],
            },
            disposition=disposition,
            analyst_review_required=disposition in {
                ReviewDisposition.MAJOR_DISAGREEMENT,
                ReviewDisposition.CRITICAL_DIVERGENCE,
            },
        )
