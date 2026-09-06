from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping


@dataclass(frozen=True)
class RiskDimension:
    key: str
    weight: float
    description: str


class CorporateRiskEngine:
    """Deterministic multi-factor corporate risk engine.

    All input factors are normalized to 0-100 where 100 represents maximum risk.
    The engine does not use an LLM to generate scores. AI models may explain the
    resulting score, drivers, uncertainty, and evidence in a separate layer.
    """

    DIMENSIONS: List[RiskDimension] = [
        RiskDimension("financial_resilience", 0.24, "Balance-sheet, liquidity, leverage, profitability and refinancing stress."),
        RiskDimension("market_stress", 0.16, "Equity, credit, volatility, valuation and market-implied stress."),
        RiskDimension("supply_chain", 0.20, "Supplier, facility, logistics, commodity and chokepoint concentration."),
        RiskDimension("geopolitical", 0.16, "Country, conflict, trade-control and political exposure."),
        RiskDimension("sanctions_compliance", 0.14, "Sanctions, export-control, counterparty and regulatory exposure."),
        RiskDimension("governance_operational", 0.10, "Governance, cyber, operational continuity and management risk."),
    ]

    @staticmethod
    def _clamp(value: float) -> float:
        return round(max(0.0, min(100.0, float(value))), 2)

    @staticmethod
    def risk_level(score: float) -> str:
        if score >= 85:
            return "Critical"
        if score >= 70:
            return "High"
        if score >= 55:
            return "Elevated"
        if score >= 35:
            return "Guarded"
        return "Low"

    def score(self, factors: Mapping[str, float], evidence_coverage: Mapping[str, float] | None = None) -> Dict[str, object]:
        normalized: Dict[str, float] = {}
        weighted_components: Dict[str, float] = {}
        missing: List[str] = []

        for dimension in self.DIMENSIONS:
            if dimension.key not in factors:
                missing.append(dimension.key)
                value = 50.0
            else:
                value = self._clamp(factors[dimension.key])

            normalized[dimension.key] = value
            weighted_components[dimension.key] = round(value * dimension.weight, 3)

        score = self._clamp(sum(weighted_components.values()))

        if evidence_coverage:
            coverage_values = [
                self._clamp(evidence_coverage.get(dimension.key, 0.0))
                for dimension in self.DIMENSIONS
            ]
            confidence = self._clamp(sum(coverage_values) / len(coverage_values))
        else:
            observed = len(self.DIMENSIONS) - len(missing)
            confidence = self._clamp((observed / len(self.DIMENSIONS)) * 100.0)

        ranked_drivers = sorted(
            (
                {
                    "dimension": dimension.key,
                    "score": normalized[dimension.key],
                    "weight": dimension.weight,
                    "weighted_contribution": weighted_components[dimension.key],
                    "description": dimension.description,
                }
                for dimension in self.DIMENSIONS
            ),
            key=lambda item: item["weighted_contribution"],
            reverse=True,
        )

        return {
            "overall_risk_score": score,
            "risk_level": self.risk_level(score),
            "confidence_score": confidence,
            "methodology": "deterministic_weighted_multifactor_v1",
            "dimensions": normalized,
            "weighted_components": weighted_components,
            "top_drivers": ranked_drivers[:3],
            "missing_dimensions": missing,
            "weights": {dimension.key: dimension.weight for dimension in self.DIMENSIONS},
        }

    def propagate_supply_chain_shock(
        self,
        base_score: float,
        dependency_share: float,
        disruption_probability: float,
        substitutability: float,
        recovery_difficulty: float,
    ) -> Dict[str, object]:
        """Translate a supply-chain shock into incremental corporate financial risk.

        Inputs are 0-100 except dependency_share, which is also represented as a
        percentage. Higher substitutability reduces the propagated shock.
        """
        base = self._clamp(base_score)
        dependency = self._clamp(dependency_share) / 100.0
        probability = self._clamp(disruption_probability) / 100.0
        substitution_penalty = 1.0 - (self._clamp(substitutability) / 100.0)
        recovery = self._clamp(recovery_difficulty) / 100.0

        raw_shock = 100.0 * dependency * probability * substitution_penalty
        recovery_multiplier = 0.5 + (0.5 * recovery)
        incremental_risk = self._clamp(raw_shock * recovery_multiplier)
        post_shock = self._clamp(base + incremental_risk * (1.0 - base / 100.0))

        return {
            "base_risk_score": base,
            "incremental_risk": incremental_risk,
            "post_shock_risk_score": post_shock,
            "post_shock_risk_level": self.risk_level(post_shock),
            "transmission": {
                "dependency_share": self._clamp(dependency_share),
                "disruption_probability": self._clamp(disruption_probability),
                "substitutability": self._clamp(substitutability),
                "recovery_difficulty": self._clamp(recovery_difficulty),
            },
            "methodology": "supply_chain_to_corporate_risk_propagation_v1",
        }
