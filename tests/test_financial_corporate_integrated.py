import unittest

from services.financial_corporate.orchestrator import FinancialCorporateOrchestrator


class FinancialCorporateIntegratedTests(unittest.TestCase):
    def setUp(self):
        self.orchestrator = FinancialCorporateOrchestrator()

    @staticmethod
    def observations():
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

    def test_full_snapshot_is_deterministic_and_resolves_entity(self):
        result = self.orchestrator.build_snapshot(
            entity_reference="NVDA",
            financial_observations=self.observations(),
            market_analysis={"market_stress_score": 70, "confidence_score": 90},
            credit_analysis={"credit_conditions_score": 65, "confidence_score": 85},
            supply_chain_risk=75,
            geopolitical_risk=50,
            sanctions_risk=10,
            governance_operational_risk=35,
        )
        self.assertEqual(result["entity"]["entity_id"], "corp_nvidia")
        self.assertFalse(result["ai_generated_score"])
        self.assertIsNotNone(result["overall"]["overall_risk_score"])
        # Confidence now reflects actual evidence quality/coverage rather than
        # treating every present scalar score as 100%-covered evidence.
        self.assertGreater(result["overall"]["confidence_score"], 70)
        self.assertLess(result["overall"]["confidence_score"], 100)
        self.assertIsNotNone(result["distress"]["distress_score"])
        self.assertEqual(result["methodology"], "financial_corporate_integrated_snapshot_v3_dynamic_hazards")
        self.assertEqual(result["overall"]["assessment_status"], "complete")

    def test_missing_cross_module_inputs_reduce_confidence_and_remain_missing(self):
        result = self.orchestrator.build_snapshot(
            entity_reference="AAPL",
            financial_observations=self.observations(),
            market_analysis={"market_stress_score": 30, "confidence_score": 80},
            credit_analysis={"credit_conditions_score": 40, "confidence_score": 80},
        )
        self.assertEqual(result["entity"]["entity_id"], "corp_apple")
        self.assertLess(result["overall"]["confidence_score"], 60)
        self.assertIsNone(result["overall"]["dimensions"]["supply_chain"])
        self.assertIsNone(result["overall"]["dimensions"]["geopolitical"])
        self.assertIn("supply_chain", result["overall"]["missing_dimensions"])
        self.assertIn("geopolitical", result["overall"]["missing_dimensions"])
        self.assertEqual(result["overall"]["assessment_status"], "partial")

    def test_snapshot_uses_reported_ratios_for_distress(self):
        result = self.orchestrator.build_snapshot(
            financial_observations=self.observations(),
            market_analysis={"market_stress_score": 85, "confidence_score": 100},
            credit_analysis={"credit_conditions_score": 80, "confidence_score": 100},
            supply_chain_risk=80,
            geopolitical_risk=70,
            sanctions_risk=20,
            governance_operational_risk=50,
        )
        ratios = result["fundamentals"]["ratios"]
        self.assertAlmostEqual(ratios["liabilities_to_assets"], 0.72, places=2)
        self.assertAlmostEqual(ratios["current_ratio"], 260 / 240, places=3)
        self.assertGreater(result["distress"]["confidence_score"], 80)


if __name__ == "__main__":
    unittest.main()
