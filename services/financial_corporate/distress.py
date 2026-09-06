from __future__ import annotations

import math
from typing import Any, Dict, Optional


class CorporateDistressEngine:
    """Deterministic corporate distress/default-risk signal engine.

    This engine does not claim a calibrated probability of default. It produces a
    transparent distress score from balance-sheet, earnings, cash-flow, and market
    stress evidence. A calibrated PD model can later be trained on historical
    defaults without changing this API contract.
    """

    @staticmethod
    def _clamp(value: float) -> float:
        return round(max(0.0, min(100.0, float(value))), 2)

    @staticmethod
    def _safe(value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            value = float(value)
            if math.isnan(value) or math.isinf(value):
                return None
            return value
        except (TypeError, ValueError):
            return None

    @staticmethod
    def distress_level(score: float) -> str:
        if score >= 85:
            return "Critical"
        if score >= 70:
            return "High"
        if score >= 55:
            return "Elevated"
        if score >= 35:
            return "Guarded"
        return "Low"

    def score(
        self,
        *,
        liabilities_to_assets: Optional[float] = None,
        current_ratio: Optional[float] = None,
        interest_coverage: Optional[float] = None,
        net_margin: Optional[float] = None,
        operating_cash_flow_to_debt: Optional[float] = None,
        market_stress_score: Optional[float] = None,
        credit_conditions_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        components: Dict[str, Dict[str, float]] = {}

        x = self._safe(liabilities_to_assets)
        if x is not None:
            components["balance_sheet"] = {"score": self._clamp((x - 0.35) / 0.55 * 100), "weight": 0.24}

        x = self._safe(current_ratio)
        if x is not None:
            components["liquidity"] = {"score": self._clamp((1.75 - x) / 1.25 * 100), "weight": 0.18}

        x = self._safe(interest_coverage)
        if x is not None:
            components["debt_service"] = {"score": self._clamp((4.0 - x) / 4.0 * 100), "weight": 0.18}

        x = self._safe(net_margin)
        if x is not None:
            components["earnings_quality"] = {"score": self._clamp((0.10 - x) / 0.25 * 100), "weight": 0.12}

        x = self._safe(operating_cash_flow_to_debt)
        if x is not None:
            components["cash_flow_coverage"] = {"score": self._clamp((0.40 - x) / 0.40 * 100), "weight": 0.12}

        x = self._safe(market_stress_score)
        if x is not None:
            components["market_stress"] = {"score": self._clamp(x), "weight": 0.10}

        x = self._safe(credit_conditions_score)
        if x is not None:
            components["funding_environment"] = {"score": self._clamp(x), "weight": 0.06}

        if not components:
            return {
                "distress_score": None,
                "distress_level": "Unknown",
                "confidence_score": 0.0,
                "components": {},
                "methodology": "corporate_distress_signal_v1",
                "calibrated_probability_of_default": False,
            }

        available_weight = sum(item["weight"] for item in components.values())
        weighted_sum = sum(item["score"] * item["weight"] for item in components.values())
        score = self._clamp(weighted_sum / available_weight)
        confidence = self._clamp(available_weight * 100)

        ranked = sorted(
            (
                {"dimension": key, **value, "weighted_contribution": round(value["score"] * value["weight"] / available_weight, 2)}
                for key, value in components.items()
            ),
            key=lambda item: item["weighted_contribution"],
            reverse=True,
        )

        return {
            "distress_score": score,
            "distress_level": self.distress_level(score),
            "confidence_score": confidence,
            "components": components,
            "top_drivers": ranked[:4],
            "methodology": "corporate_distress_signal_v1",
            "calibrated_probability_of_default": False,
            "interpretation": "Screening signal for corporate financial distress; not a rating or calibrated probability of default.",
        }
