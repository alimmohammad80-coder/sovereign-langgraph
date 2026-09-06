from __future__ import annotations

from typing import Any, Dict, Optional


class CorporateFundamentalsAnalyzer:
    """Convert normalized financial observations into transparent ratios and risk.

    This is an intentionally conservative v1 scoring layer. Missing observations
    reduce evidence coverage rather than being silently treated as healthy.
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
    def _ratio(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
        if numerator is None or denominator in (None, 0):
            return None
        return numerator / denominator

    @staticmethod
    def _clamp(value: float) -> float:
        return round(max(0.0, min(100.0, float(value))), 2)

    def analyze(self, observations: Dict[str, Any]) -> Dict[str, Any]:
        assets = self._value(observations, "assets")
        liabilities = self._value(observations, "liabilities")
        equity = self._value(observations, "equity")
        cash = self._value(observations, "cash")
        current_assets = self._value(observations, "current_assets")
        current_liabilities = self._value(observations, "current_liabilities")
        debt = self._value(observations, "long_term_debt")
        revenue = self._value(observations, "revenue")
        net_income = self._value(observations, "net_income")
        operating_income = self._value(observations, "operating_income")
        interest_expense = self._value(observations, "interest_expense")
        operating_cash_flow = self._value(observations, "operating_cash_flow")

        ratios = {
            "liabilities_to_assets": self._ratio(liabilities, assets),
            "debt_to_equity": self._ratio(debt, equity),
            "current_ratio": self._ratio(current_assets, current_liabilities),
            "cash_to_liabilities": self._ratio(cash, liabilities),
            "net_margin": self._ratio(net_income, revenue),
            "operating_margin": self._ratio(operating_income, revenue),
            "interest_coverage": self._ratio(operating_income, abs(interest_expense) if interest_expense is not None else None),
            "operating_cash_flow_to_debt": self._ratio(operating_cash_flow, debt),
        }

        components: Dict[str, float] = {}

        if ratios["liabilities_to_assets"] is not None:
            x = ratios["liabilities_to_assets"]
            components["balance_sheet_leverage"] = self._clamp((x - 0.35) / 0.55 * 100)

        if ratios["debt_to_equity"] is not None:
            x = ratios["debt_to_equity"]
            components["debt_burden"] = self._clamp(x / 3.0 * 100)

        if ratios["current_ratio"] is not None:
            x = ratios["current_ratio"]
            components["liquidity"] = self._clamp((2.0 - x) / 1.5 * 100)

        if ratios["interest_coverage"] is not None:
            x = ratios["interest_coverage"]
            components["interest_service"] = self._clamp((5.0 - x) / 5.0 * 100)

        if ratios["net_margin"] is not None:
            x = ratios["net_margin"]
            components["profitability"] = self._clamp((0.15 - x) / 0.30 * 100)

        if ratios["operating_cash_flow_to_debt"] is not None:
            x = ratios["operating_cash_flow_to_debt"]
            components["cash_flow_debt_coverage"] = self._clamp((0.50 - x) / 0.50 * 100)

        if components:
            financial_risk = self._clamp(sum(components.values()) / len(components))
        else:
            financial_risk = 50.0

        expected = 6
        coverage = self._clamp(len(components) / expected * 100)

        return {
            "financial_resilience_risk_score": financial_risk,
            "risk_direction": "higher_is_worse",
            "evidence_coverage": coverage,
            "ratios": {key: round(value, 4) if value is not None else None for key, value in ratios.items()},
            "components": components,
            "methodology": "fundamental_ratio_risk_v1",
            "notes": [
                "Scores are deterministic and derived only from available reported observations.",
                "Cross-period normalization and sector-relative calibration will be added in later model versions.",
            ],
        }
