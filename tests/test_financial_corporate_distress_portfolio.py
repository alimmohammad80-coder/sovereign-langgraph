import unittest

from services.financial_corporate.distress import CorporateDistressEngine
from services.financial_corporate.portfolio import PortfolioRiskEngine


class CorporateDistressEngineTests(unittest.TestCase):
    def test_high_stress_company_scores_high(self):
        engine = CorporateDistressEngine()
        result = engine.score(
            liabilities_to_assets=0.9,
            current_ratio=0.6,
            interest_coverage=0.7,
            net_margin=-0.12,
            operating_cash_flow_to_debt=0.05,
            market_stress_score=82,
            credit_conditions_score=74,
        )
        self.assertGreaterEqual(result["distress_score"], 70)
        self.assertIn(result["distress_level"], {"High", "Critical"})
        self.assertFalse(result["calibrated_probability_of_default"])

    def test_missing_data_reduces_confidence(self):
        engine = CorporateDistressEngine()
        result = engine.score(current_ratio=1.1)
        self.assertIsNotNone(result["distress_score"])
        self.assertLess(result["confidence_score"], 50)


class PortfolioRiskEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = PortfolioRiskEngine()
        self.positions = [
            {"entity_id": "corp_tsmc", "market_value": 600, "risk_score": 75, "sector": "Technology", "country_iso3": "TWN"},
            {"entity_id": "corp_nvidia", "market_value": 250, "risk_score": 55, "sector": "Technology", "country_iso3": "USA"},
            {"entity_id": "corp_jpm", "market_value": 150, "risk_score": 40, "sector": "Financials", "country_iso3": "USA"},
        ]

    def test_portfolio_concentration(self):
        result = self.engine.analyze(self.positions)
        self.assertEqual(result["position_count"], 3)
        self.assertEqual(result["largest_position_weight"], 60.0)
        self.assertGreater(result["concentration_score"], 50)

    def test_scenario_loss(self):
        result = self.engine.stress_test(
            self.positions,
            {"corp_tsmc": -30, "corp_nvidia": -20, "corp_jpm": -5},
        )
        self.assertLess(result["portfolio_loss_pct"], 0)
        self.assertLess(result["post_shock_value_pct"], 100)

    def test_contagion_propagates(self):
        result = self.engine.contagion(
            {"corp_tsmc": 90},
            [
                {"source_entity_id": "corp_tsmc", "target_entity_id": "corp_nvidia", "weight": 0.7},
                {"source_entity_id": "corp_nvidia", "target_entity_id": "corp_jpm", "weight": 0.3},
            ],
            rounds=3,
        )
        self.assertGreater(result["final_stress"].get("corp_nvidia", 0), 0)
        self.assertGreater(result["final_stress"].get("corp_jpm", 0), 0)


if __name__ == "__main__":
    unittest.main()
