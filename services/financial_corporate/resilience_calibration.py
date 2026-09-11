from __future__ import annotations

from typing import Any, Dict, Mapping, Optional


class FinancialResilienceCalibrationEngine:
    """Blend validated depth evidence into Financial Resilience.

    Base fundamentals remain the anchor. New evidence is capped and
    confidence-weighted so partial depth coverage cannot dominate the score.
    """

    WEIGHTS = {
        "fundamentals": 0.55,
        "debt_refinancing": 0.15,
        "credit_vulnerability": 0.15,
        "financial_trends": 0.10,
        "sector_relative": 0.05,
    }

    @staticmethod
    def _num(value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            return max(0.0, min(100.0, float(value)))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _result(score: Optional[float], **payload: Any) -> Dict[str, Any]:
        # calibrated_risk_score is a presentation compatibility alias. The
        # authoritative field remains financial_resilience_risk_score.
        return {
            "financial_resilience_risk_score": score,
            "calibrated_risk_score": score,
            **payload,
        }

    def calibrate(
        self,
        *,
        fundamentals: Optional[Mapping[str, Any]],
        debt_refinancing: Optional[Mapping[str, Any]] = None,
        credit_vulnerability: Optional[Mapping[str, Any]] = None,
        financial_trends: Optional[Mapping[str, Any]] = None,
        sector_relative: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        candidates = {
            "fundamentals": (
                self._num((fundamentals or {}).get("financial_resilience_risk_score")),
                self._num((fundamentals or {}).get("evidence_coverage")) or 0.0,
            ),
            "debt_refinancing": (
                self._num((debt_refinancing or {}).get("refinancing_risk_score")),
                self._num((debt_refinancing or {}).get("confidence_score")) or 0.0,
            ),
            "credit_vulnerability": (
                self._num((credit_vulnerability or {}).get("credit_vulnerability_score")),
                self._num((credit_vulnerability or {}).get("confidence_score")) or 0.0,
            ),
            "financial_trends": (
                self._num((financial_trends or {}).get("trend_risk_score")),
                self._num((financial_trends or {}).get("confidence_score")) or 0.0,
            ),
            "sector_relative": (
                self._num((sector_relative or {}).get("sector_relative_risk_score")),
                self._num((sector_relative or {}).get("confidence_score")) or 0.0,
            ),
        }

        observed: Dict[str, Dict[str, float]] = {}
        for key, (score, confidence) in candidates.items():
            if score is None or confidence <= 0:
                continue
            observed[key] = {
                "score": score,
                "confidence": confidence,
                "base_weight": self.WEIGHTS[key],
                "effective_weight": self.WEIGHTS[key] * (confidence / 100.0),
            }

        fundamentals_score = candidates["fundamentals"][0]
        if fundamentals_score is None:
            return self._result(
                None,
                confidence_score=0.0,
                assessment_status="insufficient_evidence",
                components=observed,
                methodology="financial_resilience_calibrated_v1",
                ai_generated_score=False,
            )

        denominator = sum(item["effective_weight"] for item in observed.values())
        if denominator <= 0:
            return self._result(
                fundamentals_score,
                confidence_score=candidates["fundamentals"][1],
                assessment_status="base_only",
                components=observed,
                methodology="financial_resilience_calibrated_v1",
                ai_generated_score=False,
            )

        score = sum(item["score"] * item["effective_weight"] for item in observed.values()) / denominator
        lower = fundamentals_score - 15.0
        upper = fundamentals_score + 15.0
        score = max(lower, min(upper, score))
        score = round(max(0.0, min(100.0, score)), 2)

        intended_weight_coverage = sum(self.WEIGHTS[key] for key in observed)
        confidence = sum(
            item["confidence"] * item["base_weight"] for item in observed.values()
        )

        return self._result(
            score,
            base_fundamentals_score=fundamentals_score,
            score_delta=round(score - fundamentals_score, 2),
            confidence_score=round(max(0.0, min(100.0, confidence)), 2),
            evidence_coverage=round(intended_weight_coverage * 100.0, 2),
            assessment_status="complete" if intended_weight_coverage >= 0.95 else "partial",
            components=observed,
            guardrails={"max_delta_from_fundamentals": 15.0},
            methodology="financial_resilience_calibrated_v1",
            ai_generated_score=False,
        )
