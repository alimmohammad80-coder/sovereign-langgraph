from __future__ import annotations

from typing import Any, Dict, Optional


class FinancialSensitivityAnalyzer:
    """Deterministic rate and FX sensitivity using only reported observations.

    Rate shocks translate debt exposure into incremental interest expense and
    post-shock interest coverage. FX sensitivity is emitted only when a reported
    foreign-revenue or foreign-cost share exists.
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

    def analyze(self, observations: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        observations = observations or {}
        debt = self._value(observations, "long_term_debt")
        current_debt = self._value(observations, "current_debt")
        interest_expense = self._value(observations, "interest_expense")
        operating_income = self._value(observations, "operating_income")
        revenue = self._value(observations, "revenue")
        foreign_revenue_share = self._value(observations, "foreign_revenue_share")
        foreign_cost_share = self._value(observations, "foreign_cost_share")

        total_debt = debt
        if total_debt is None:
            total_debt = current_debt
        elif current_debt is not None:
            total_debt += current_debt

        rate_scenarios = []
        if total_debt is not None and operating_income is not None:
            baseline_interest = abs(interest_expense) if interest_expense is not None else 0.0
            for shock_bps in (100, 200, 300):
                incremental_interest = total_debt * (shock_bps / 10000.0)
                stressed_interest = baseline_interest + incremental_interest
                stressed_coverage = operating_income / stressed_interest if stressed_interest > 0 else None
                coverage_risk = None
                if stressed_coverage is not None:
                    coverage_risk = self._clamp((5.0 - stressed_coverage) / 5.0 * 100.0)
                rate_scenarios.append({
                    "shock_bps": shock_bps,
                    "incremental_interest_expense": round(incremental_interest, 2),
                    "stressed_interest_expense": round(stressed_interest, 2),
                    "stressed_interest_coverage": round(stressed_coverage, 4) if stressed_coverage is not None else None,
                    "coverage_risk_score": coverage_risk,
                })
            rate_status = "observed"
        else:
            rate_status = "insufficient_evidence"

        fx_scenarios = []
        fx_share = foreign_revenue_share if foreign_revenue_share is not None else foreign_cost_share
        fx_basis = "foreign_revenue_share" if foreign_revenue_share is not None else (
            "foreign_cost_share" if foreign_cost_share is not None else None
        )
        if revenue is not None and fx_share is not None:
            normalized_share = fx_share / 100.0 if fx_share > 1 else fx_share
            normalized_share = max(0.0, min(1.0, normalized_share))
            for move_pct in (5, 10, 20):
                gross_exposure = revenue * normalized_share * (move_pct / 100.0)
                fx_scenarios.append({
                    "fx_move_pct": move_pct,
                    "gross_revenue_equivalent_exposure": round(gross_exposure, 2),
                    "exposure_share": round(normalized_share * 100.0, 2),
                    "direction": "gross_exposure_only",
                })
            fx_status = "observed"
        else:
            fx_status = "insufficient_evidence"

        worst_rate_risk = max(
            (row["coverage_risk_score"] for row in rate_scenarios if row.get("coverage_risk_score") is not None),
            default=None,
        )
        observed_sections = sum(1 for status in (rate_status, fx_status) if status == "observed")

        return {
            "rate_sensitivity": {
                "status": rate_status,
                "total_debt": total_debt,
                "baseline_interest_expense": abs(interest_expense) if interest_expense is not None else None,
                "scenarios": rate_scenarios,
                "worst_case_coverage_risk_score": worst_rate_risk,
            },
            "fx_sensitivity": {
                "status": fx_status,
                "basis": fx_basis,
                "scenarios": fx_scenarios,
                "note": "FX output is gross exposure, not earnings-at-risk, unless hedging and currency-specific disclosures are available.",
            },
            "evidence_coverage": round(observed_sections / 2 * 100.0, 2),
            "methodology": "financial_rates_fx_sensitivity_v1",
            "ai_generated_score": False,
        }
