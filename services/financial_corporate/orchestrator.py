from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from .distress import CorporateDistressEngine
from .entity_master import CorporateEntityMaster
from .fundamentals import CorporateFundamentalsAnalyzer
from .market_credit import MarketCreditIntelligenceService
from .risk_engine import CorporateRiskEngine


class FinancialCorporateOrchestrator:
    """Compose normalized evidence into one corporate intelligence snapshot."""

    def __init__(self) -> None:
        self.entity_master = CorporateEntityMaster()
        self.fundamentals = CorporateFundamentalsAnalyzer()
        self.market_credit = MarketCreditIntelligenceService()
        self.distress = CorporateDistressEngine()
        self.corporate_risk = CorporateRiskEngine()

    @staticmethod
    def _score(value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            return max(0.0, min(100.0, float(value)))
        except (TypeError, ValueError):
            return None

    @classmethod
    def _cross_module_confidence(
        cls,
        evidence: Optional[Mapping[str, Any]],
        dimension: str,
        *,
        score_present: bool,
    ) -> float:
        """Return evidence confidence for one cross-module risk dimension.

        Risk presence and evidence confidence are intentionally separate. A
        dimension can be scored while still relying on aging, indirect, or
        partial evidence. Live cross-module edges carry their own confidence and
        are averaged here instead of granting every observed dimension 100%.
        """
        cross_module = (evidence or {}).get("cross_module") if isinstance(evidence, Mapping) else None
        dimension_evidence = (cross_module or {}).get("evidence") if isinstance(cross_module, Mapping) else None
        rows = (dimension_evidence or {}).get(dimension) if isinstance(dimension_evidence, Mapping) else None

        confidences = []
        for row in rows or []:
            if not isinstance(row, Mapping):
                continue
            value = cls._score(row.get("confidence"))
            if value is not None:
                confidences.append(value)

        if confidences:
            return round(sum(confidences) / len(confidences), 2)
        # Direct/manual risk inputs without provenance should not be treated as
        # fully evidenced. Preserve them as usable but explicitly moderate.
        return 60.0 if score_present else 0.0

    def build_snapshot(
        self,
        *,
        entity_reference: Optional[str] = None,
        financial_observations: Optional[Dict[str, Any]] = None,
        market_analysis: Optional[Dict[str, Any]] = None,
        credit_analysis: Optional[Dict[str, Any]] = None,
        supply_chain_risk: Optional[float] = None,
        geopolitical_risk: Optional[float] = None,
        sanctions_risk: Optional[float] = None,
        governance_operational_risk: Optional[float] = None,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        entity = self.entity_master.resolve(entity_reference) if entity_reference else None

        fundamentals = self.fundamentals.analyze(financial_observations) if financial_observations else None
        combined_market_credit = self.market_credit.combined_score(
            market_analysis=market_analysis,
            credit_analysis=credit_analysis,
        )

        ratios = (fundamentals or {}).get("ratios") or {}
        distress = self.distress.score(
            liabilities_to_assets=ratios.get("liabilities_to_assets"),
            current_ratio=ratios.get("current_ratio"),
            interest_coverage=ratios.get("interest_coverage"),
            net_margin=ratios.get("net_margin"),
            operating_cash_flow_to_debt=ratios.get("operating_cash_flow_to_debt"),
            market_stress_score=(market_analysis or {}).get("market_stress_score"),
            credit_conditions_score=(credit_analysis or {}).get("credit_conditions_score"),
        )

        financial_score = self._score((fundamentals or {}).get("financial_resilience_risk_score"))
        market_score = self._score(combined_market_credit.get("market_credit_stress_score"))

        factors = {
            "financial_resilience": financial_score,
            "market_stress": market_score,
            "supply_chain": self._score(supply_chain_risk),
            "geopolitical": self._score(geopolitical_risk),
            "sanctions_compliance": self._score(sanctions_risk),
            "governance_operational": self._score(governance_operational_risk),
        }

        evidence_coverage = {
            "financial_resilience": self._score((fundamentals or {}).get("evidence_coverage")) or 0.0,
            "market_stress": self._score(combined_market_credit.get("confidence_score")) or 0.0,
            "supply_chain": self._cross_module_confidence(
                evidence, "supply_chain", score_present=supply_chain_risk is not None
            ),
            "geopolitical": self._cross_module_confidence(
                evidence, "geopolitical", score_present=geopolitical_risk is not None
            ),
            "sanctions_compliance": self._cross_module_confidence(
                evidence, "sanctions_compliance", score_present=sanctions_risk is not None
            ),
            "governance_operational": self._cross_module_confidence(
                evidence, "governance_operational", score_present=governance_operational_risk is not None
            ),
        }

        risk = self.corporate_risk.score(factors, evidence_coverage)
        risk["dimension_confidence"] = evidence_coverage
        risk["confidence_interpretation"] = (
            "Weighted evidence confidence across all six risk dimensions; dimensional coverage and source confidence are distinct."
        )

        return {
            "entity": entity,
            "overall": risk,
            "distress": distress,
            "fundamentals": fundamentals,
            "market_credit": combined_market_credit,
            "inputs": {
                "supply_chain_risk": supply_chain_risk,
                "geopolitical_risk": geopolitical_risk,
                "sanctions_risk": sanctions_risk,
                "governance_operational_risk": governance_operational_risk,
            },
            "evidence": evidence or {},
            "methodology": "financial_corporate_integrated_snapshot_v4_evidence_confidence",
            "ai_generated_score": False,
        }
