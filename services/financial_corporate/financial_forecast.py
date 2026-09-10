from __future__ import annotations

from typing import Any, Dict, Mapping, Optional


class FinancialRiskForecastEngine:
    """Directional, deterministic near-term financial-risk forecasting.

    Forecasts are scenario-style risk trajectories, not event probabilities.
    They use current authoritative risk plus observed momentum from trends,
    refinancing, credit vulnerability, market stress, and external hazards.
    """

    HORIZONS = {"30d": 0.35, "90d": 0.70, "180d": 1.00}

    @staticmethod
    def _num(value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            return max(0.0, min(100.0, float(value)))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _signed_pressure(score: Optional[float], neutral: float = 50.0) -> Optional[float]:
        if score is None:
            return None
        return (score - neutral) / 50.0

    def forecast(
        self,
        *,
        current_risk_score: Any,
        confidence_score: Any,
        market_stress_score: Any = None,
        refinancing_risk_score: Any = None,
        credit_vulnerability_score: Any = None,
        trend_risk_score: Any = None,
        supply_chain_risk: Any = None,
        geopolitical_risk: Any = None,
    ) -> Dict[str, Any]:
        base = self._num(current_risk_score)
        confidence = self._num(confidence_score) or 0.0
        if base is None:
            return {
                "assessment_status": "insufficient_evidence",
                "horizons": {},
                "methodology": "financial_risk_directional_forecast_v1",
                "probability_forecast": False,
                "ai_generated_score": False,
            }

        raw_inputs = {
            "market_stress": self._num(market_stress_score),
            "refinancing": self._num(refinancing_risk_score),
            "credit_vulnerability": self._num(credit_vulnerability_score),
            "financial_trends": self._num(trend_risk_score),
            "supply_chain": self._num(supply_chain_risk),
            "geopolitical": self._num(geopolitical_risk),
        }
        weights = {
            "market_stress": 0.24,
            "refinancing": 0.18,
            "credit_vulnerability": 0.20,
            "financial_trends": 0.18,
            "supply_chain": 0.10,
            "geopolitical": 0.10,
        }

        pressures = []
        weight_sum = 0.0
        for key, value in raw_inputs.items():
            p = self._signed_pressure(value)
            if p is None:
                continue
            w = weights[key]
            pressures.append((key, p, w))
            weight_sum += w

        if not pressures:
            return {
                "assessment_status": "base_only",
                "base_risk_score": base,
                "confidence_score": confidence,
                "horizons": {h: {"risk_score": base, "direction": "stable", "delta": 0.0} for h in self.HORIZONS},
                "drivers": [],
                "methodology": "financial_risk_directional_forecast_v1",
                "probability_forecast": False,
                "ai_generated_score": False,
            }

        composite_pressure = sum(p * w for _, p, w in pressures) / weight_sum
        # Confidence dampens trajectory magnitude. Maximum 180d movement is 18 points.
        confidence_scalar = 0.35 + 0.65 * (confidence / 100.0)
        max_delta = 18.0 * composite_pressure * confidence_scalar

        horizons: Dict[str, Any] = {}
        for horizon, scalar in self.HORIZONS.items():
            delta = round(max_delta * scalar, 2)
            projected = round(max(0.0, min(100.0, base + delta)), 2)
            direction = "deteriorating" if delta >= 2.0 else "improving" if delta <= -2.0 else "stable"
            horizons[horizon] = {
                "risk_score": projected,
                "delta": delta,
                "direction": direction,
            }

        drivers = sorted(
            [
                {"factor": key, "score": raw_inputs[key], "signed_pressure": round(p, 3), "weight": w}
                for key, p, w in pressures
            ],
            key=lambda item: abs(item["signed_pressure"] * item["weight"]),
            reverse=True,
        )

        return {
            "assessment_status": "complete" if weight_sum >= 0.8 else "partial",
            "base_risk_score": base,
            "confidence_score": confidence,
            "input_weight_coverage": round(weight_sum * 100.0, 2),
            "composite_pressure": round(composite_pressure, 4),
            "horizons": horizons,
            "drivers": drivers,
            "interpretation": "Directional risk trajectory; not a calibrated probability of default or event occurrence.",
            "methodology": "financial_risk_directional_forecast_v1",
            "probability_forecast": False,
            "ai_generated_score": False,
        }
