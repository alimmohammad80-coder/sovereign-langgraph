import unittest

from services.financial_corporate.cross_module_edges import CrossModuleExposureBridge
from services.financial_corporate.portfolio import PortfolioRiskEngine


class CrossModuleExposureBridgeTests(unittest.TestCase):
    def setUp(self):
        self.bridge = CrossModuleExposureBridge()

    def test_supply_chain_edge_normalizes_percent_share(self):
        result = self.bridge.from_supply_chain([
            {
                "company_entity_id": "corp_tsmc",
                "port_id": "port_kaohsiung",
                "dependency_share": 72,
                "confidence": 90,
            }
        ])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source_entity_id"], "port_kaohsiung")
        self.assertEqual(result[0]["target_entity_id"], "corp_tsmc")
        self.assertEqual(result[0]["weight"], 0.72)

    def test_country_edge_uses_country_node(self):
        result = self.bridge.from_country([
            {
                "company_entity_id": "corp_apple",
                "country_iso3": "CHN",
                "revenue_share": 18,
            }
        ])
        self.assertEqual(result[0]["source_entity_id"], "country:CHN")
        self.assertEqual(result[0]["weight"], 0.18)

    def test_build_deduplicates_same_edge_by_confidence(self):
        result = self.bridge.build({
            "supply_chain": [
                {"company_entity_id": "corp_nvidia", "supplier_entity_id": "corp_tsmc", "weight": 0.6, "confidence": 50},
                {"company_entity_id": "corp_nvidia", "supplier_entity_id": "corp_tsmc", "weight": 0.6, "confidence": 90},
            ]
        })
        self.assertEqual(result["edge_count"], 1)
        self.assertEqual(result["edges"][0]["confidence"], 90)

    def test_multi_module_contagion_reaches_company(self):
        built = self.bridge.build({
            "country": [
                {"company_entity_id": "corp_tsmc", "country_iso3": "TWN", "exposure_share": 1.0, "confidence": 95}
            ],
            "supply_chain": [
                {"company_entity_id": "corp_nvidia", "supplier_entity_id": "corp_tsmc", "weight": 0.7, "confidence": 90}
            ],
        })
        engine = PortfolioRiskEngine()
        contagion = engine.contagion(
            initial_shocks={"country:TWN": 80},
            edges=built["edges"],
            rounds=2,
            damping=0.65,
        )
        self.assertGreater(contagion["final_stress"].get("corp_tsmc", 0), 0)
        self.assertGreater(contagion["final_stress"].get("corp_nvidia", 0), 0)


if __name__ == "__main__":
    unittest.main()
