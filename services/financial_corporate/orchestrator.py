from __future__ import annotations

from typing import Any, Dict, Optional

from .credit_conditions import CreditConditionsEngine
from .distress import CorporateDistressEngine
from .entity_master import CorporateEntityMaster
from .fundamentals import CorporateFundamentalsAnalyzer
from .market_credit import MarketCreditIntelligenceService
from .market_data import MarketDataEngine
from .risk_engine import CorporateRiskEngine


class FinancialCorporateOrchestrator:
    """Compose normalized evidence into one corporate intelligence snapshot.

    This service deliberately accepts already-normalized evidence so it is fully
    testable without live external APIs. Live collectors are invoked by route-level
    adapters and their output is passed into this orchestrator.
    """

    def __init__(self) -> None:
        self.entity_master = CorporateEntityMaster()
        self.fundamentals = CorporateFundamentalsAnalyzer()
        self.market_engine = MarketDataEngine()
        self.credit_engine = CreditConditionsEngine()
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

        fundamentals = None
        if financial_observations:
            fundamentals = self.fundamentals.analyze(financial_observations)

        combined_market_credit = self.market_credit.combine(
            market_analysis=market_analysis,
            credit_analysis=credit_analysis,
        )

        financial_score = self._score((fundamentals or {}).get("financial_resilience_risk_score"))
        market_score = self._score(combined_market_credit.get("market_credit_risk_score"))

        distress = self.distress.score(
            financial_analysis=fundamentals or {},
            market_analysis=market_analysis or {},
            credit_analysis=credit_analysis or {},
        )

        factors = {
            "financial_resilience": financial_score if financial_score is not None else 50.0,
            "market_stress": market_score if market_score is not None else 50.0,
            "supply_chain": self._score(supply_chain_risk) if supply_chain_risk is not None else 50.0,
            "geopolitical": self._score(geopolitical_risk) if geopolitical_risk is not None else 50.0,
            "sanctions_compliance": self._score(sanctions_risk) if sanctions_risk is not None else 50.0,
            "governance_operational": self._score(governance_operational_risk) if governance_operational_risk is not None else 50.0,
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
            "methodology": "financial_corporate_integrated_snapshot_v1",
            "ai_generated_score": False,
        }
