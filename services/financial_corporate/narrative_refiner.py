from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any, Dict, Mapping, Optional

from app.ai_gateway.factory import get_ai_gateway
from app.ai_gateway.schemas import AIGatewayRequest, AIResponseFormat, AITaskType


NARRATIVE_SYSTEM_PROMPT = """You are the constrained analytical narrative layer for Sovereign Intelligence AI.

You receive a validated Financial & Corporate Risk Intelligence report whose deterministic scores, evidence registry, claims, classifications, and forecast horizons are authoritative.

Your task is ONLY to improve executive synthesis and readability. You must not create, alter, infer, recalculate, normalize, round, or override any risk score, confidence score, probability, evidence item, source, attribution category, sanctions finding, cyber incident attribution, or forecast horizon.

Rules:
1. Use only the supplied validated claims and evidence registry.
2. Every section summary and refined key judgment must cite one or more existing evidence_ids.
3. Do not introduce evidence_ids that are not supplied.
4. A sanctions or watchlist no-match is not zero sanctions risk.
5. Downstream diversion exposure is not company misconduct, sanctions evasion, or non-compliance.
6. Product vulnerabilities, supplier incidents, ecosystem cyber events, and company co-mentions are not direct enterprise incidents unless the validated claims explicitly attribute the company as the victim.
7. Forecasts are directional unless an upstream calibrated probability is explicitly present. Do not invent event probabilities.
8. Do not output any score fields, probability fields, confidence fields, or source objects.
9. When evidence is incomplete, preserve uncertainty rather than filling gaps.
10. Return JSON only.

Required JSON shape:
{
  "bluf": "executive synthesis",
  "section_summaries": {
    "existing_section_key": {"text": "synthesis", "evidence_ids": ["existing-id"]}
  },
  "key_judgments": [
    {"text": "judgment", "evidence_ids": ["existing-id"]}
  ],
  "analytic_caveats": ["short caveat"]
}
"""


class NarrativeValidationError(ValueError):
    pass


class FinancialCorporateNarrativeRefiner:
    """Model-assisted prose refinement with a fail-closed evidence contract.

    The deterministic report always remains the authoritative analytical object.
    Model output is accepted only as a prose overlay after structural, citation,
    semantic, and score-authority validation. Any failure returns the original
    report unchanged apart from refinement metadata.
    """

    _FORBIDDEN_KEYS = {
        "score",
        "risk_score",
        "overall_risk_score",
        "confidence",
        "confidence_score",
        "probability",
        "likelihood",
        "risk_level",
        "assessment",
        "evidence_registry",
        "citations",
        "sources",
        "source",
    }

    _PROHIBITED_LEGAL_OR_NEGATIVE_SCREENING = (
        re.compile(r"\b(?:zero|no) sanctions risk\b", re.IGNORECASE),
        re.compile(r"\b(?:zero|no) cyber risk\b", re.IGNORECASE),
        re.compile(r"\bcompany (?:committed|engaged in) misconduct\b", re.IGNORECASE),
        re.compile(r"\b(?:violated|evaded) sanctions\b", re.IGNORECASE),
        re.compile(r"\bsanctions non[- ]compliance\b", re.IGNORECASE),
    )

    _INVENTED_PROBABILITY = re.compile(
        r"\b(?:probability|chance|likelihood)\b[^.\n]{0,35}\b\d{1,3}(?:\.\d+)?%",
        re.IGNORECASE,
    )

    def __init__(self, gateway: Any = None) -> None:
        self._gateway = gateway

    @staticmethod
    def _evidence_id_set(report: Mapping[str, Any]) -> set[str]:
        return {
            str(item.get("evidence_id"))
            for item in report.get("evidence_registry") or []
            if item.get("evidence_id")
        }

    @staticmethod
    def _claim_package(report: Mapping[str, Any]) -> Dict[str, Any]:
        sections: Dict[str, Any] = {}
        for section_key, section in (report.get("sections") or {}).items():
            sections[section_key] = {
                "title": section.get("title"),
                "claims": [
                    {
                        "claim_type": claim.get("claim_type"),
                        "text": claim.get("text"),
                        "evidence_ids": claim.get("evidence_ids") or [],
                        "horizon": claim.get("horizon"),
                    }
                    for claim in section.get("claims") or []
                ],
            }

        evidence = []
        for item in report.get("evidence_registry") or []:
            evidence.append({
                "evidence_id": item.get("evidence_id"),
                "source": item.get("source"),
                "title": item.get("title"),
                "published": item.get("published"),
                "evidence_type": item.get("evidence_type"),
                "status": item.get("status"),
                "attribution_category": item.get("attribution_category"),
                "freshness_status": item.get("freshness_status"),
            })

        return {
            "entity": report.get("entity") or {},
            "assessment_context": {
                "risk_score": (report.get("assessment") or {}).get("risk_score"),
                "risk_level": (report.get("assessment") or {}).get("risk_level"),
                "confidence": (report.get("assessment") or {}).get("confidence"),
                "assessment_status": (report.get("assessment") or {}).get("assessment_status"),
                "score_authority": "integrated_snapshot",
            },
            "baseline_bluf": report.get("bluf"),
            "sections": sections,
            "evidence_registry": evidence,
            "evidence_gaps": report.get("evidence_gaps") or [],
            "indicators_to_watch": report.get("indicators_to_watch") or [],
            "constraints": {
                "scores_are_locked": True,
                "citations_must_use_existing_evidence_ids": True,
                "negative_screening_is_not_zero_risk": True,
                "diversion_is_not_misconduct": True,
                "cyber_attribution_must_remain_separated": True,
                "forecasts_are_directional_unless_explicitly_calibrated": True,
            },
        }

    @classmethod
    def _walk_forbidden_keys(cls, value: Any, path: str = "root") -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                normalized = str(key).strip().lower()
                if normalized in cls._FORBIDDEN_KEYS:
                    raise NarrativeValidationError(f"forbidden_model_field:{path}.{key}")
                cls._walk_forbidden_keys(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                cls._walk_forbidden_keys(child, f"{path}[{index}]")

    @classmethod
    def _validate_text(cls, text: Any) -> str:
        if not isinstance(text, str) or not text.strip():
            raise NarrativeValidationError("empty_or_non_string_narrative")
        normalized = " ".join(text.split())
        for pattern in cls._PROHIBITED_LEGAL_OR_NEGATIVE_SCREENING:
            if pattern.search(normalized):
                raise NarrativeValidationError("prohibited_semantic_overreach")
        if cls._INVENTED_PROBABILITY.search(normalized):
            raise NarrativeValidationError("invented_event_probability")
        return normalized

    @staticmethod
    def _validate_refs(refs: Any, allowed: set[str]) -> list[str]:
        if not isinstance(refs, list) or not refs:
            raise NarrativeValidationError("missing_evidence_reference")
        normalized = [str(ref) for ref in refs]
        unknown = [ref for ref in normalized if ref not in allowed]
        if unknown:
            raise NarrativeValidationError("unknown_evidence_reference:" + ",".join(sorted(set(unknown))))
        return normalized

    @classmethod
    def validate_candidate(cls, candidate: Mapping[str, Any], report: Mapping[str, Any]) -> Dict[str, Any]:
        if not isinstance(candidate, Mapping):
            raise NarrativeValidationError("model_output_not_object")
        cls._walk_forbidden_keys(candidate)

        allowed_keys = {"bluf", "section_summaries", "key_judgments", "analytic_caveats"}
        extra_keys = set(candidate.keys()) - allowed_keys
        if extra_keys:
            raise NarrativeValidationError("unexpected_model_fields:" + ",".join(sorted(extra_keys)))

        allowed_refs = cls._evidence_id_set(report)
        section_keys = set((report.get("sections") or {}).keys())

        bluf = cls._validate_text(candidate.get("bluf"))

        raw_summaries = candidate.get("section_summaries") or {}
        if not isinstance(raw_summaries, Mapping):
            raise NarrativeValidationError("section_summaries_not_object")
        summaries: Dict[str, Dict[str, Any]] = {}
        for section_key, item in raw_summaries.items():
            if section_key not in section_keys:
                raise NarrativeValidationError(f"unknown_section:{section_key}")
            if not isinstance(item, Mapping):
                raise NarrativeValidationError(f"section_summary_not_object:{section_key}")
            summaries[section_key] = {
                "text": cls._validate_text(item.get("text")),
                "evidence_ids": cls._validate_refs(item.get("evidence_ids"), allowed_refs),
            }

        raw_judgments = candidate.get("key_judgments") or []
        if not isinstance(raw_judgments, list):
            raise NarrativeValidationError("key_judgments_not_list")
        judgments = []
        for item in raw_judgments[:8]:
            if not isinstance(item, Mapping):
                raise NarrativeValidationError("key_judgment_not_object")
            judgments.append({
                "text": cls._validate_text(item.get("text")),
                "evidence_ids": cls._validate_refs(item.get("evidence_ids"), allowed_refs),
            })

        raw_caveats = candidate.get("analytic_caveats") or []
        if not isinstance(raw_caveats, list):
            raise NarrativeValidationError("analytic_caveats_not_list")
        caveats = [cls._validate_text(item) for item in raw_caveats[:8]]

        return {
            "bluf": bluf,
            "section_summaries": summaries,
            "key_judgments": judgments,
            "analytic_caveats": caveats,
        }

    @staticmethod
    def _overlay(report: Mapping[str, Any], validated: Mapping[str, Any], metadata: Mapping[str, Any]) -> Dict[str, Any]:
        refined = deepcopy(dict(report))
        refined["baseline_bluf"] = report.get("bluf")
        refined["bluf"] = validated.get("bluf")
        refined["refined_key_judgments"] = validated.get("key_judgments") or []
        refined["analytic_caveats"] = validated.get("analytic_caveats") or []

        for section_key, summary in (validated.get("section_summaries") or {}).items():
            if section_key in (refined.get("sections") or {}):
                refined["sections"][section_key]["narrative_summary"] = dict(summary)

        refined["narrative_refinement"] = {
            "status": "accepted",
            "score_authority": "integrated_snapshot",
            "model_can_modify_scores": False,
            **dict(metadata),
        }
        return refined

    def refine(
        self,
        report: Mapping[str, Any],
        *,
        preferred_provider: Optional[str] = None,
        preferred_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        baseline = deepcopy(dict(report))
        gateway = self._gateway or get_ai_gateway()

        try:
            available = gateway.available_providers()
        except Exception as exc:
            baseline["narrative_refinement"] = {
                "status": "fallback",
                "reason": f"gateway_status_error:{type(exc).__name__}",
                "score_authority": "integrated_snapshot",
                "model_can_modify_scores": False,
            }
            return baseline

        if not available:
            baseline["narrative_refinement"] = {
                "status": "fallback",
                "reason": "no_configured_ai_provider",
                "score_authority": "integrated_snapshot",
                "model_can_modify_scores": False,
            }
            return baseline

        package = self._claim_package(report)
        request = AIGatewayRequest(
            task_type=AITaskType.STRATEGIC_REVIEW,
            system_prompt=NARRATIVE_SYSTEM_PROMPT,
            user_prompt=json.dumps(package, ensure_ascii=False, separators=(",", ":")),
            preferred_provider=preferred_provider,
            preferred_model=preferred_model,
            response_format=AIResponseFormat.JSON,
            temperature=0.1,
            max_tokens=5000,
            metadata={
                "required_json_keys": [
                    "bluf",
                    "section_summaries",
                    "key_judgments",
                    "analytic_caveats",
                ]
            },
        )

        try:
            response = gateway.generate(request)
            if not isinstance(response.parsed_json, Mapping):
                raise NarrativeValidationError("provider_returned_no_json_object")
            validated = self.validate_candidate(response.parsed_json, report)
            return self._overlay(
                report,
                validated,
                {
                    "provider": response.provider,
                    "model": response.model,
                    "latency_ms": response.latency_ms,
                    "validation": "pass",
                    "fallback_used": bool((response.metadata or {}).get("fallback_used")),
                },
            )
        except Exception as exc:
            baseline["narrative_refinement"] = {
                "status": "fallback",
                "reason": f"{type(exc).__name__}:{exc}",
                "score_authority": "integrated_snapshot",
                "model_can_modify_scores": False,
            }
            return baseline
