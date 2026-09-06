from __future__ import annotations

from typing import Any, Dict, Optional

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
            "supply_chain": 100.0 if supply_chain_risk is not None else 0.0,
            "geopolitical": 100.0 if geopolitical_risk is not None else 0.0,
            "sanctions_compliance": 100.0 if sanctions_risk is not None else 0.0,
            "governance_operational": 100.0 if governance_operational_risk is not None else 0.0,
        }

        risk = self.corporate_risk.score(factors, evidence_coverage)

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
            "methodology": "financial_corporate_integrated_snapshot_v3_dynamic_hazards",
            "ai_generated_score": False,
        }
