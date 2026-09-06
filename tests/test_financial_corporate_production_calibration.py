import unittest

from services.financial_corporate.production_calibration import ProductionCalibratedCorporateHazardService


class ProductionOperationalCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.service = ProductionCalibratedCorporateHazardService()
        self.entity = {
            "entity_id": "corp_nvidia",
            "common_name": "NVIDIA",
            "legal_name": "NVIDIA Corporation",
            "identifiers": {},
        }

    def test_product_cves_cannot_create_near_critical_operational_score(self):
        result = self.service.governance_operational_composite(
            sec_disclosure={"score": None},
            enterprise_incident={"score": None},
            cisa_kev={"score": None},
            nvd={"score": 90, "confidence": 90},
            cyber_media={"score": 82, "confidence": 88},
        )
        self.assertLessEqual(result["score"], 55.0)
        components = {item["component"]: item for item in result["components"]}
        self.assertEqual(components["product_security_nvd"]["score"], 55.0)
        self.assertEqual(components["cyber_media_context"]["score"], 35.0)

    def test_sec_material_disclosure_has_highest_weight(self):
        result = self.service.governance_operational_composite(
            sec_disclosure={"score": 90, "confidence": 98},
            enterprise_incident={"score": 70, "confidence": 90},
            cisa_kev={"score": 60, "confidence": 90},
            nvd={"score": 80, "confidence": 90},
            cyber_media={"score": 80, "confidence": 80},
        )
        self.assertGreater(result["score"], 70.0)
        components = {item["component"]: item for item in result["components"]}
        self.assertEqual(components["sec_material_cyber_disclosure"]["base_weight"], 0.40)

    def test_openai_attack_headline_is_not_direct_nvidia_incident(self):
        media = {
            "matched_items": [
                {
                    "title": "Nvidia, SpaceX, Microsoft launch AI safety initiative as OpenAI cyberattack fallout continues",
                    "source_quality_weight": 1.0,
                    "freshness_weight": 0.9,
                    "signal_severity": "high",
                    "relevance": "direct",
                }
            ]
        }
        result = self.service.direct_enterprise_incident_pressure(self.entity, media)
        self.assertIsNone(result["score"])
        self.assertEqual(result["status"], "screened_no_direct_enterprise_incident")

    def test_confirmed_nvidia_breach_is_direct_enterprise_incident(self):
        media = {
            "matched_items": [
                {
                    "title": "NVIDIA confirms GeForce NOW data breach affecting users",
                    "source_quality_weight": 1.0,
                    "freshness_weight": 0.9,
                    "signal_severity": "high",
                    "relevance": "direct",
                }
            ]
        }
        result = self.service.direct_enterprise_incident_pressure(self.entity, media)
        self.assertEqual(result["status"], "observed")
        self.assertGreater(result["score"], 50.0)


if __name__ == "__main__":
    unittest.main()
