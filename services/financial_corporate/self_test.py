from __future__ import annotations

from typing import Any, Dict, List

from .cross_module_edges import CrossModuleExposureBridge
from .entity_master import CorporateEntityMaster
from .orchestrator import FinancialCorporateOrchestrator
from .portfolio import PortfolioRiskEngine


class FinancialCorporateSelfTest:
    """Dependency-free deterministic runtime checks for module readiness."""

    def __init__(self) -> None:
        self.master = CorporateEntityMaster()
        self.orchestrator = FinancialCorporateOrchestrator()
        self.bridge = CrossModuleExposureBridge()
        self.portfolio = PortfolioRiskEngine()

    @staticmethod
    def _observations() -> Dict[str, Dict[str, float]]:
        return {
            "assets": {"value": 1000},
            "liabilities": {"value": 720},
            "equity": {"value": 280},
            "cash": {"value": 90},
            "current_assets": {"value": 260},
            "current_liabilities": {"value": 240},
            "long_term_debt": {"value": 340},
            "revenue": {"value": 800},
            "net_income": {"value": 32},
            "operating_income": {"value": 60},
            "interest_expense": {"value": 30},
            "operating_cash_flow": {"value": 80},
        }

    def run(self) -> Dict[str, Any]:
        checks: List[Dict[str, Any]] = []

        def record(name: str, passed: bool, detail: Any = None) -> None:
            checks.append({"name": name, "passed": bool(passed), "detail": detail})

        nvda = self.master.resolve("NVDA")
        record("entity_resolution", bool(nvda and nvda.get("entity_id") == "corp_nvidia"), nvda)

        snapshot = self.orchestrator.build_snapshot(
            entity_reference="NVDA",
            financial_observations=self._observations(),
            market_analysis={"market_stress_score": 70, "confidence_score": 90},
            credit_analysis={"credit_conditions_score": 65, "confidence_score": 85},
            supply_chain_risk=75,
            geopolitical_risk=50,
            sanctions_risk=10,
            governance_operational_risk=35,
        )
        score = snapshot.get("overall", {}).get("overall_risk_score")
        confidence = snapshot.get("overall", {}).get("confidence_score")
        record("integrated_snapshot", score is not None and 0 <= score <= 100, {"score": score, "confidence": confidence})
        record("non_ai_scoring", snapshot.get("ai_generated_score") is False)

        edge_graph = self.bridge.build({
            "country": [{
                "source_id": "country_TWN",
                "target_entity_id": "corp_tsmc",
                "relationship_type": "country_exposure",
                "weight": 0.9,
                "confidence": 90,
            }],
            "supply_chain": [{
                "source_entity_id": "corp_tsmc",
                "target_entity_id": "corp_nvidia",
                "relationship_type": "supplier_dependency",
                "weight": 0.8,
                "confidence": 90,
            }],
        })
        record("cross_module_edges", edge_graph.get("edge_count") == 2, edge_graph.get("by_module"))

        contagion = self.portfolio.contagion(
            initial_shocks={"country_TWN": 90},
            edges=edge_graph.get("edges", []),
            rounds=3,
            damping=0.65,
        )
        final = contagion.get("final_stress", {})
        record(
            "multi_hop_contagion",
            float(final.get("corp_tsmc", 0)) > 0 and float(final.get("corp_nvidia", 0)) > 0,
            final,
        )

        passed = sum(1 for check in checks if check["passed"])
        return {
            "status": "pass" if passed == len(checks) else "fail",
            "passed": passed,
            "total": len(checks),
            "checks": checks,
            "methodology": "financial_corporate_runtime_self_test_v1",
        }
