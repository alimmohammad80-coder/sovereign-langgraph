from __future__ import annotations

from typing import Any, Dict, Optional

from .credit_conditions import CreditConditionsAnalyzer, FREDCreditConditionsCollector
from .market_data import AlphaVantageMarketCollector, MarketStressAnalyzer


class MarketCreditIntelligenceService:
    """Combine company market stress with system credit conditions."""

    def __init__(self) -> None:
        self.market_collector = AlphaVantageMarketCollector()
        self.market_analyzer = MarketStressAnalyzer()
        self.credit_collector = FREDCreditConditionsCollector()
        self.credit_analyzer = CreditConditionsAnalyzer()

    @staticmethod
    def _clamp(value: float) -> float:
        return round(max(0.0, min(100.0, float(value))), 2)

    def provider_status(self) -> Dict[str, Any]:
        return {
            "alpha_vantage": {
                "configured": self.market_collector.configured,
                "role": "company-specific daily equity market history",
            },
            "fred": {
                "configured": True,
                "role": "system credit, rates and funding conditions",
            },
        }

    def company_market_snapshot(self, symbol: str) -> Dict[str, Any]:
        market_data = self.market_collector.daily_prices(symbol)
        analysis = self.market_analyzer.analyze(market_data)
        return {
            "symbol": symbol.upper(),
            "market_data": market_data,
            "analysis": analysis,
        }

    def credit_snapshot(self) -> Dict[str, Any]:
        raw = self.credit_collector.snapshot()
        analysis = self.credit_analyzer.analyze(raw)
        return {"credit_data": raw, "analysis": analysis}

    def combined_score(
        self,
        symbol: Optional[str] = None,
        market_analysis: Optional[Dict[str, Any]] = None,
        credit_analysis: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        errors = []
        if market_analysis is None and symbol:
            try:
                market_analysis = self.company_market_snapshot(symbol)["analysis"]
            except Exception as exc:
                errors.append({"component": "market", "error": str(exc)})
        if credit_analysis is None:
            try:
                credit_analysis = self.credit_snapshot()["analysis"]
            except Exception as exc:
                errors.append({"component": "credit", "error": str(exc)})

        components: Dict[str, Dict[str, float]] = {}
        if market_analysis and market_analysis.get("market_stress_score") is not None:
            components["equity_market"] = {
                "score": self._clamp(market_analysis["market_stress_score"]),
                "confidence": self._clamp(market_analysis.get("confidence_score", 0.0)),
                "base_weight": 0.65,
            }
        if credit_analysis and credit_analysis.get("credit_conditions_score") is not None:
            components["credit_conditions"] = {
                "score": self._clamp(credit_analysis["credit_conditions_score"]),
                "confidence": self._clamp(credit_analysis.get("confidence_score", 0.0)),
                "base_weight": 0.35,
            }

        if not components:
            return {
                "market_credit_stress_score": None,
                "confidence_score": 0.0,
                "assessment_status": "insufficient_evidence",
                "evidence_coverage": 0.0,
                "methodology": "confidence_weighted_market_credit_v2_coverage_aware",
                "components": {},
                "errors": errors,
                "ai_generated_score": False,
            }

        effective_weights: Dict[str, float] = {}
        for key, item in components.items():
            effective_weights[key] = item["base_weight"] * (item["confidence"] / 100.0)
        denominator = sum(effective_weights.values())
        if denominator <= 0:
            score = sum(item["score"] * item["base_weight"] for item in components.values()) / sum(
                item["base_weight"] for item in components.values()
            )
        else:
            score = sum(components[key]["score"] * weight for key, weight in effective_weights.items()) / denominator

        # Confidence measures coverage of the intended 65/35 evidence stack,
        # not merely confidence conditional on whichever components happened to
        # be available. Thus credit-only evidence with 100% source confidence
        # yields 35% market-credit confidence rather than a misleading 100%.
        confidence = sum(
            item["confidence"] * item["base_weight"]
            for item in components.values()
        )
        evidence_coverage = sum(item["base_weight"] for item in components.values()) * 100.0

        if len(components) == 2:
            assessment_status = "complete"
        else:
            assessment_status = "partial"

        return {
            "market_credit_stress_score": self._clamp(score),
            "confidence_score": self._clamp(confidence),
            "assessment_status": assessment_status,
            "evidence_coverage": self._clamp(evidence_coverage),
            "methodology": "confidence_weighted_market_credit_v2_coverage_aware",
            "components": components,
            "effective_weights": {key: round(value, 4) for key, value in effective_weights.items()},
            "errors": errors,
            "ai_generated_score": False,
        }
