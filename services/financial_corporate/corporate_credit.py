from __future__ import annotations

from typing import Any, Dict, Optional


class CorporateCreditVulnerabilityAnalyzer:
    """Company-specific credit vulnerability from reported balance-sheet evidence."""

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
        debt_refinancing: Optional[Dict[str, Any]] = None,
        credit_conditions: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        observations = observations or {}
        debt_refinancing = debt_refinancing or {}
        credit_conditions = credit_conditions or {}

        debt = self._value(observations, "long_term_debt")
        current_debt = self._value(observations, "current_debt")
        cash = self._value(observations, "cash")
        equity = self._value(observations, "equity")
        operating_income = self._value(observations, "operating_income")
        interest_expense = self._value(observations, "interest_expense")
        operating_cash_flow = self._value(observations, "operating_cash_flow")
        current_assets = self._value(observations, "current_assets")
        current_liabilities = self._value(observations, "current_liabilities")

        total_debt = debt
        if total_debt is None:
            total_debt = current_debt
        elif current_debt is not None:
            total_debt += current_debt

        net_debt = total_debt - cash if total_debt is not None and cash is not None else None
        metrics = {
            "debt_to_equity": total_debt / equity if total_debt is not None and equity not in (None, 0) else None,
            "net_debt_to_equity": net_debt / equity if net_debt is not None and equity not in (None, 0) else None,
            "interest_coverage": operating_income / abs(interest_expense) if operating_income is not None and interest_expense not in (None, 0) else None,
            "cash_flow_to_debt": operating_cash_flow / total_debt if operating_cash_flow is not None and total_debt not in (None, 0) else None,
            "current_ratio": current_assets / current_liabilities if current_assets is not None and current_liabilities not in (None, 0) else None,
        }

        components: Dict[str, float] = {}
        if metrics["debt_to_equity"] is not None:
            components["leverage"] = self._clamp(metrics["debt_to_equity"] / 3.0 * 100.0)
        if metrics["interest_coverage"] is not None:
            components["interest_service"] = self._clamp((5.0 - metrics["interest_coverage"]) / 5.0 * 100.0)
        if metrics["cash_flow_to_debt"] is not None:
            components["cash_flow_coverage"] = self._clamp((0.5 - metrics["cash_flow_to_debt"]) / 0.5 * 100.0)
        if metrics["current_ratio"] is not None:
            components["liquidity"] = self._clamp((2.0 - metrics["current_ratio"]) / 1.5 * 100.0)

        refinancing_score = debt_refinancing.get("refinancing_risk_score")
        try:
            if refinancing_score is not None:
                components["refinancing"] = self._clamp(float(refinancing_score))
        except (TypeError, ValueError):
            pass

        system_credit = credit_conditions.get("credit_conditions_score")
        try:
            if system_credit is not None:
                components["system_credit_environment"] = self._clamp(float(system_credit))
        except (TypeError, ValueError):
            pass

        if components:
            # Company fundamentals dominate; system conditions are intentionally capped in influence.
            weights = {
                "leverage": 0.22,
                "interest_service": 0.22,
                "cash_flow_coverage": 0.18,
                "liquidity": 0.13,
                "refinancing": 0.17,
                "system_credit_environment": 0.08,
            }
            denominator = sum(weights[key] for key in components)
            score = sum(components[key] * weights[key] for key in components) / denominator
            score = self._clamp(score)
            status = "complete" if len(components) >= 5 else "partial"
        else:
            score = None
            status = "insufficient_evidence"

        return {
            "credit_vulnerability_score": score,
            "risk_direction": "higher_is_worse",
            "assessment_status": status,
            "evidence_coverage": self._clamp(len(components) / 6.0 * 100.0),
            "metrics": {key: round(value, 4) if value is not None else None for key, value in metrics.items()},
            "components": components,
            "methodology": "company_credit_vulnerability_v1",
            "ai_generated_score": False,
        }
