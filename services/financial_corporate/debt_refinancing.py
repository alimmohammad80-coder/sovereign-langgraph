from __future__ import annotations

from typing import Any, Dict, Optional


class DebtRefinancingAnalyzer:
    """Assess debt maturity concentration and refinancing pressure from reported evidence.

    Missing maturity buckets are reported as unknown. The analyzer never converts
    absent disclosure into a neutral score.
    """

    @staticmethod
    def _value(observations: Dict[str, Any], key: str) -> Optional[float]:
        item = observations.get(key)
        if not isinstance(item, dict) or item.get("value") is None:
            return None
        try:
            return float(item["value"])
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _clamp(value: float) -> float:
        return round(max(0.0, min(100.0, float(value))), 2)

    def analyze(
        self,
        observations: Optional[Dict[str, Any]],
        debt_maturities: Optional[Dict[str, Any]],
        credit_analysis: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        observations = observations or {}
        debt_maturities = debt_maturities or {}

        cash = self._value(observations, "cash")
        current_debt = self._value(observations, "current_debt")
        long_term_debt = self._value(observations, "long_term_debt")
        operating_cash_flow = self._value(observations, "operating_cash_flow")

        buckets: Dict[str, Optional[float]] = {}
        for key in ("year_1", "year_2", "year_3", "year_4", "year_5", "thereafter"):
            item = debt_maturities.get(key)
            try:
                buckets[key] = float(item["value"]) if isinstance(item, dict) and item.get("value") is not None else None
            except (TypeError, ValueError):
                buckets[key] = None

        reported = {key: value for key, value in buckets.items() if value is not None}
        near_term = sum(value for key, value in reported.items() if key in {"year_1", "year_2"}) if reported else None
        five_year = sum(value for key, value in reported.items() if key != "thereafter") if reported else None
        disclosed_total = sum(reported.values()) if reported else None

        reference_debt = long_term_debt
        if reference_debt is None and current_debt is not None:
            reference_debt = current_debt
        elif reference_debt is not None and current_debt is not None:
            reference_debt += current_debt

        metrics: Dict[str, Optional[float]] = {
            "near_term_maturities": near_term,
            "five_year_maturities": five_year,
            "disclosed_maturity_total": disclosed_total,
            "near_term_to_debt": (near_term / reference_debt) if near_term is not None and reference_debt not in (None, 0) else None,
            "cash_to_near_term_maturities": (cash / near_term) if cash is not None and near_term not in (None, 0) else None,
            "operating_cash_flow_to_near_term_maturities": (
                operating_cash_flow / near_term
                if operating_cash_flow is not None and near_term not in (None, 0)
                else None
            ),
        }

        components: Dict[str, float] = {}
        if metrics["near_term_to_debt"] is not None:
            components["maturity_concentration"] = self._clamp(metrics["near_term_to_debt"] * 140.0)
        if metrics["cash_to_near_term_maturities"] is not None:
            components["cash_refinancing_buffer"] = self._clamp((1.5 - metrics["cash_to_near_term_maturities"]) / 1.5 * 100.0)
        if metrics["operating_cash_flow_to_near_term_maturities"] is not None:
            components["cash_flow_refinancing_buffer"] = self._clamp(
                (1.0 - metrics["operating_cash_flow_to_near_term_maturities"]) * 100.0
            )

        credit_score = None
        if isinstance(credit_analysis, dict):
            try:
                raw = credit_analysis.get("credit_conditions_score")
                credit_score = float(raw) if raw is not None else None
            except (TypeError, ValueError):
                credit_score = None
        if credit_score is not None and (near_term is not None or current_debt is not None):
            components["refinancing_environment"] = self._clamp(credit_score)

        if components:
            score = self._clamp(sum(components.values()) / len(components))
            status = "complete" if len(components) >= 3 and len(reported) >= 2 else "partial"
        else:
            score = None
            status = "insufficient_evidence"

        expected_components = 4
        evidence_coverage = self._clamp(len(components) / expected_components * 100.0)
        missing = []
        if not reported:
            missing.append("debt_maturity_schedule")
        if cash is None:
            missing.append("cash")
        if operating_cash_flow is None:
            missing.append("operating_cash_flow")
        if reference_debt is None:
            missing.append("debt_balance")
        if credit_score is None:
            missing.append("credit_conditions")

        return {
            "refinancing_risk_score": score,
            "risk_direction": "higher_is_worse",
            "assessment_status": status,
            "evidence_coverage": evidence_coverage,
            "maturity_buckets": buckets,
            "metrics": {key: round(value, 4) if value is not None else None for key, value in metrics.items()},
            "components": components,
            "missing_evidence": missing,
            "methodology": "debt_maturity_refinancing_risk_v1",
            "ai_generated_score": False,
        }
