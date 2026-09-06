import unittest

from services.financial_corporate.cross_module_hazards import CrossModuleDynamicHazardService
from services.financial_corporate.cross_module_scoring import CrossModuleRiskScorer


class StubHazards(CrossModuleDynamicHazardService):
    def country_hazard(self, iso3):
        return {
            "status": "observed",
            "score": 40.0,
            "confidence": 85.0,
            "source": "Country Intelligence",
            "source_table": "country_risk_scores",
            "iso3": iso3,
        }

    def conflict_hazard(self, iso3):
        return {
            "status": "observed",
            "score": 60.0,
            "confidence": 70.0,
            "source": "Conflict Forecasting",
            "source_mode": "test_conflict_signals",
            "iso3": iso3,
        }

    def sanctions_screen(self, entity):
        return {
            "status": "screened_no_direct_match",
            "match": False,
            "score": None,
            "source": "OFAC Sanctions List Service",
        }

    def cyber_screen(self, entity):
        return {
            "status": "observed",
            "score": 50.0,
            "confidence": 90.0,
            "source": "CISA Known Exploited Vulnerabilities",
        }


class DynamicHazardScoringTests(unittest.TestCase):
    def setUp(self):
        self.scorer = CrossModuleRiskScorer()

    def test_structural_exposure_without_hazard_is_not_scored(self):
        result = self.scorer.score_company(
            "corp_nvidia",
            [
                {
                    "source_entity_id": "country:TWN",
                    "target_entity_id": "corp_nvidia",
                    "relationship_type": "semiconductor_supply_chain",
                    "weight": 1.0,
                    "source_module": "Supply Chain Intelligence",
                    "confidence": 75.0,
                    "evidence": {
                        "exposure_level": 92,
                        "severity_score": 92,
                        "severity_source": "stored_exposure_level",
                    },
                }
            ],
        )
        self.assertIsNone(result["scores"]["supply_chain"])
        self.assertEqual(result["scored_edge_count"], 0)
        self.assertEqual(result["unscored_exposures"][0]["reason"], "missing_dynamic_hazard")

    def test_exposure_hazard_confidence_formula(self):
        result = self.scorer.score_company(
            "corp_nvidia",
            [
                {
                    "source_entity_id": "country:TWN",
                    "target_entity_id": "corp_nvidia",
                    "relationship_type": "semiconductor_supply_chain",
                    "weight": 0.92,
                    "source_module": "Supply Chain Intelligence",
                    "confidence": 75.0,
                    "evidence": {
                        "structural_exposure": 0.92,
                        "hazard_score": 40.0,
                        "hazard_source": "country_risk_scores",
                    },
                }
            ],
        )
        self.assertAlmostEqual(result["scores"]["supply_chain"], 27.6, places=2)
        evidence = result["evidence"]["supply_chain"][0]
        self.assertEqual(evidence["structural_exposure"], 0.92)
        self.assertEqual(evidence["hazard_intensity"], 40.0)

    def test_dynamic_enrichment_adds_country_conflict_and_cyber_edges(self):
        service = StubHazards()
        enriched = service.enrich(
            company_entity_id="corp_nvidia",
            entity={
                "entity_id": "corp_nvidia",
                "legal_name": "NVIDIA Corporation",
                "common_name": "NVIDIA",
                "tickers": ["NVDA"],
            },
            edges=[
                {
                    "source_entity_id": "country:TWN",
                    "target_entity_id": "corp_nvidia",
                    "relationship_type": "semiconductor_supply_chain",
                    "weight": 1.0,
                    "source_module": "Supply Chain Intelligence",
                    "confidence": 75.0,
                    "evidence": {
                        "exposure_level": 92,
                        "severity_score": 92,
                        "severity_source": "stored_exposure_level",
                    },
                }
            ],
        )
        self.assertEqual(enriched["added_edge_count"], 3)
        source_modules = {edge["source_module"] for edge in enriched["edges"]}
        self.assertIn("Country Intelligence", source_modules)
        self.assertIn("Conflict Forecasting", source_modules)
        self.assertIn("Cyber & Information Operations", source_modules)
        self.assertNotIn("Sanctions / Trade Intelligence", source_modules)

        supply_edge = next(
            edge for edge in enriched["edges"]
            if edge["source_module"] == "Supply Chain Intelligence"
        )
        self.assertAlmostEqual(supply_edge["weight"], 0.92, places=4)
        self.assertEqual(supply_edge["evidence"]["hazard_score"], 60.0)
        self.assertNotIn("severity_score", supply_edge["evidence"])

        scored = self.scorer.score_company("corp_nvidia", enriched["edges"])
        self.assertAlmostEqual(scored["scores"]["supply_chain"], 41.4, places=2)
        self.assertIsNotNone(scored["scores"]["geopolitical"])
        self.assertAlmostEqual(scored["scores"]["governance_operational"], 45.0, places=2)
        self.assertIsNone(scored["scores"]["sanctions_compliance"])


if __name__ == "__main__":
    unittest.main()
