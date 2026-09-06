from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional


@dataclass(frozen=True)
class RiskDimension:
    key: str
    weight: float
    description: str


class CorporateRiskEngine:
    """Deterministic multi-factor corporate risk engine.

    All observed input factors are normalized to 0-100 where 100 represents
    maximum risk. Missing factors are treated as unknown evidence, never as a
    synthetic neutral score. The overall score is reweighted across observed
    dimensions and confidence captures evidence coverage.
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

    def score(
        self,
        factors: Mapping[str, Optional[float]],
        evidence_coverage: Mapping[str, float] | None = None,
    ) -> Dict[str, object]:
        normalized: Dict[str, Optional[float]] = {}
        weighted_components: Dict[str, Optional[float]] = {}
        effective_weights: Dict[str, float] = {}
        missing: List[str] = []
        observed_dimensions: List[RiskDimension] = []

        for dimension in self.DIMENSIONS:
            raw_value = factors.get(dimension.key)
            if raw_value is None:
                missing.append(dimension.key)
                normalized[dimension.key] = None
                weighted_components[dimension.key] = None
                continue
            value = self._clamp(raw_value)
            normalized[dimension.key] = value
            observed_dimensions.append(dimension)

        observed_weight = sum(d.weight for d in observed_dimensions)
        if observed_weight > 0:
            score_total = 0.0
            for dimension in observed_dimensions:
                effective_weight = dimension.weight / observed_weight
                effective_weights[dimension.key] = round(effective_weight, 4)
                contribution = float(normalized[dimension.key]) * effective_weight
                weighted_components[dimension.key] = round(contribution, 3)
                score_total += contribution
            score = self._clamp(score_total)
        else:
            score = None

        for dimension in self.DIMENSIONS:
            if dimension.key not in effective_weights:
                effective_weights[dimension.key] = 0.0

        if evidence_coverage:
            confidence = self._clamp(
                sum(
                    dimension.weight * self._clamp(evidence_coverage.get(dimension.key, 0.0))
                    for dimension in self.DIMENSIONS
                )
            )
        else:
            confidence = self._clamp(observed_weight * 100.0)

        ranked_drivers = sorted(
            (
                {
                    "dimension": dimension.key,
                    "score": normalized[dimension.key],
                    "weight": dimension.weight,
                    "effective_weight": effective_weights[dimension.key],
                    "weighted_contribution": weighted_components[dimension.key],
                    "description": dimension.description,
                }
                for dimension in observed_dimensions
            ),
            key=lambda item: float(item["weighted_contribution"] or 0.0),
            reverse=True,
        )

        return {
            "overall_risk_score": score,
            "risk_level": self.risk_level(score) if score is not None else "Unknown",
            "assessment_status": "complete" if not missing else ("partial" if observed_dimensions else "insufficient_evidence"),
            "confidence_score": confidence,
            "methodology": "deterministic_weighted_multifactor_v2_missing_aware",
            "dimensions": normalized,
            "weighted_components": weighted_components,
            "effective_weights": effective_weights,
            "top_drivers": ranked_drivers[:3],
            "missing_dimensions": missing,
            "observed_dimension_count": len(observed_dimensions),
            "total_dimension_count": len(self.DIMENSIONS),
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
        """Translate a supply-chain shock into incremental corporate financial risk."""
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
