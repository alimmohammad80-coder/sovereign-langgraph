from __future__ import annotations

import math
from datetime import datetime, timezone
from statistics import mean
from typing import Any

from supabase import Client

from app.schemas.sews_warning_scoring import (
    IndicatorContribution,
    WarningAssessmentRequest,
    WarningAssessmentResponse,
    WarningState,
)

FORMULA_VERSION = "sews-warning-logit-v2.0.0"


class SEWSWarningScoringError(RuntimeError):
    pass


class SEWSWarningScoringService:
    def __init__(self, db: Client):
        self.db = db

    @staticmethod
    def _logit(p: float) -> float:
        p = min(0.999999, max(0.000001, p))
        return math.log(p / (1 - p))

    @staticmethod
    def _sigmoid(x: float) -> float:
        if x >= 0:
            z = math.exp(-x)
            return 1 / (1 + z)
        z = math.exp(x)
        return z / (1 + z)

    @staticmethod
    def _probability_band(p: float) -> str:
        if p < .2: return "0–20%"
        if p < .4: return "20–40%"
        if p < .6: return "40–60%"
        if p < .8: return "60–80%"
        return "80–100%"

    @staticmethod
    def _confidence_level(score: float) -> str:
        return "HIGH" if score >= 75 else "MEDIUM" if score >= 50 else "LOW"

    @staticmethod
    def _state(p: float) -> WarningState:
        if p >= .8: return WarningState.CRITICAL
        if p >= .6: return WarningState.WARNING
        if p >= .4: return WarningState.ADVISORY
        if p >= .2: return WarningState.WATCH
        return WarningState.DORMANT

    @staticmethod
    def _direction(current: float, previous: float | None) -> str:
        if previous is None: return "STABLE"
        if current - previous >= .05: return "DETERIORATING"
        if current - previous <= -.05: return "IMPROVING"
        return "STABLE"

    def _problem(self, key: str) -> dict[str, Any]:
        result = (self.db.table("sews_warning_problems")
                  .select("id,problem_key,base_rate,severity_score,active")
                  .eq("problem_key", key).limit(1).execute())
        if not result.data:
            raise SEWSWarningScoringError(f"Unknown warning problem: {key}")
        if not result.data[0]["active"]:
            raise SEWSWarningScoringError(f"Inactive warning problem: {key}")
        return result.data[0]

    def _previous_probability(self, problem_id: str) -> float | None:
        result = (self.db.table("sews_assessments").select("probability")
                  .eq("warning_problem_id", problem_id)
                  .order("assessed_at", desc=True).limit(1).execute())
        return float(result.data[0]["probability"]) if result.data else None

    def assess(self, problem_key: str, request: WarningAssessmentRequest) -> WarningAssessmentResponse:
        problem = self._problem(problem_key)
        mappings = (self.db.table("sews_warning_problem_indicators")
                    .select("indicator_key,indicator_class,weight,polarity,required")
                    .eq("problem_key", problem_key).eq("active", True).execute().data or [])
        if not mappings:
            raise SEWSWarningScoringError(f"No indicator mappings for {problem_key}")

        keys = [m["indicator_key"] for m in mappings]
        query = self.db.table("sews_indicator_state").select(
            "indicator_key,current_value,confidence,status,freshness_score"
        ).in_("indicator_key", keys)
        if request.country_iso3:
            query = query.eq("country_iso3", request.country_iso3.upper())
        if request.region_key:
            query = query.eq("region_key", request.region_key)
        states = {r["indicator_key"]: r for r in (query.execute().data or [])}

        contributions: list[IndicatorContribution] = []
        support = contra = dark = 0
        for mapping in mappings:
            state = states.get(mapping["indicator_key"])
            if not state or state.get("current_value") is None:
                if mapping.get("required"): dark += 1
                continue
            confidence = float(state.get("confidence") or 0)
            if confidence < request.minimum_indicator_confidence:
                continue
            status = str(state.get("status") or "UNKNOWN")
            if status in {"STALE", "DEGRADED", "INSUFFICIENT_EVIDENCE"}: dark += 1
            value = float(state["current_value"])
            signed = (value - .5) * 2
            if mapping["indicator_class"] == "CONTRA": signed *= -1
            signed *= float(mapping.get("polarity") or 1)
            quality = max(.05, (confidence / 100) * (float(state.get("freshness_score") or 0) / 100))
            weighted = signed * float(mapping.get("weight") or 1) * quality
            support += weighted >= 0
            contra += weighted < 0
            contributions.append(IndicatorContribution(
                indicator_key=mapping["indicator_key"],
                indicator_class=mapping["indicator_class"],
                current_value=round(value, 4),
                confidence=round(confidence, 2),
                weight=round(float(mapping.get("weight") or 1), 4),
                polarity=round(float(mapping.get("polarity") or 1), 4),
                weighted_contribution=round(weighted, 6),
                status=status,
            ))

        if len(contributions) < request.minimum_indicator_count:
            raise SEWSWarningScoringError(
                f"Insufficient usable indicator states: {len(contributions)} available, "
                f"{request.minimum_indicator_count} required"
            )

        evidence_sum = sum(c.weighted_contribution for c in contributions)
        probability = round(self._sigmoid(self._logit(float(problem["base_rate"])) + evidence_sum), 4)
        coverage = len(contributions) / max(1, len(mappings))
        mean_conf = mean(c.confidence for c in contributions) / 100
        healthy = sum(c.status == "ACTIVE" for c in contributions) / len(contributions)
        balance = 1 - contra / max(1, support + contra)
        breakdown = {
            "indicator_coverage": round(coverage, 4),
            "mean_indicator_confidence": round(mean_conf, 4),
            "collection_integrity": round(healthy, 4),
            "evidence_balance": round(balance, 4),
        }
        confidence_score = round((coverage*.35 + mean_conf*.30 + healthy*.20 + balance*.15) * 100, 2)
        previous = self._previous_probability(str(problem["id"]))
        assessed_at = datetime.now(timezone.utc)
        payload = {
            "problem_key": problem_key,
            "base_rate": float(problem["base_rate"]),
            "evidence_sum": round(evidence_sum, 6),
            "previous_probability": previous,
            "country_iso3": request.country_iso3,
            "region_key": request.region_key,
        }
        assessment_id = None
        if request.persist:
            row = {
                "warning_problem_id": problem["id"],
                "assessed_at": assessed_at.isoformat(),
                "probability": probability,
                "probability_band": self._probability_band(probability),
                "confidence_score": confidence_score,
                "confidence_level": self._confidence_level(confidence_score),
                "severity_score": float(problem["severity_score"]),
                "recommended_state": self._state(probability).value,
                "indicator_snapshot": [c.model_dump(mode="json") for c in contributions],
                "confidence_breakdown": breakdown,
                "formula_version": FORMULA_VERSION,
                "deterministic_payload": payload,
            }
            result = self.db.table("sews_assessments").insert(row).execute()
            if not result.data:
                raise SEWSWarningScoringError("Assessment insert returned no row")
            assessment_id = result.data[0]["id"]

        return WarningAssessmentResponse(
            problem_key=problem_key,
            warning_problem_id=problem["id"],
            assessed_at=assessed_at,
            probability=probability,
            probability_band=self._probability_band(probability),
            confidence_score=confidence_score,
            confidence_level=self._confidence_level(confidence_score),
            severity_score=float(problem["severity_score"]),
            recommended_state=self._state(probability),
            direction=self._direction(probability, previous),
            indicator_count=len(contributions),
            supporting_count=support,
            contradicting_count=contra,
            dark_or_stale_count=dark,
            indicator_contributions=sorted(contributions, key=lambda c: abs(c.weighted_contribution), reverse=True),
            confidence_breakdown=breakdown,
            formula_version=FORMULA_VERSION,
            assessment_id=assessment_id,
            persisted=request.persist,
            deterministic_payload=payload,
        )
