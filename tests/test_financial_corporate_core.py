import unittest

from services.financial_corporate.entity_master import CorporateEntityMaster
from services.financial_corporate.risk_engine import CorporateRiskEngine


class CorporateEntityMasterTests(unittest.TestCase):
    def setUp(self):
        self.master = CorporateEntityMaster()

    def test_resolves_common_name(self):
        entity = self.master.resolve("TSMC")
        self.assertIsNotNone(entity)
        self.assertEqual(entity["entity_id"], "corp_tsmc")

    def test_resolves_ticker(self):
        entity = self.master.resolve("NVDA")
        self.assertIsNotNone(entity)
        self.assertEqual(entity["entity_id"], "corp_nvidia")

    def test_country_filter(self):
        entities = self.master.list_entities(country_iso3="USA", limit=50)
        self.assertTrue(entities)
        self.assertTrue(all(entity["country_iso3"] == "USA" for entity in entities))


class CorporateRiskEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = CorporateRiskEngine()

    def test_weighted_score(self):
        result = self.engine.score({
            "financial_resilience": 80,
            "market_stress": 70,
            "supply_chain": 90,
            "geopolitical": 60,
            "sanctions_compliance": 20,
            "governance_operational": 40,
        })
        self.assertEqual(result["overall_risk_score"], 64.8)
        self.assertEqual(result["risk_level"], "Elevated")
        self.assertEqual(result["confidence_score"], 100.0)
        self.assertFalse(result["missing_dimensions"])

    def test_thresholds_follow_platform_risk_scale(self):
        self.assertEqual(self.engine.risk_level(34.99), "Low")
        self.assertEqual(self.engine.risk_level(35), "Guarded")
        self.assertEqual(self.engine.risk_level(55), "Elevated")
        self.assertEqual(self.engine.risk_level(70), "High")
        self.assertEqual(self.engine.risk_level(85), "Critical")

    def test_supply_chain_shock_increases_risk(self):
        result = self.engine.propagate_supply_chain_shock(
            base_score=50,
            dependency_share=72,
            disruption_probability=80,
            substitutability=20,
            recovery_difficulty=75,
        )
        self.assertGreater(result["post_shock_risk_score"], result["base_risk_score"])
        self.assertGreater(result["incremental_risk"], 0)


if __name__ == "__main__":
    unittest.main()
