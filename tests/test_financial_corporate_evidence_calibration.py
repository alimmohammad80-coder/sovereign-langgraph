import unittest

from services.financial_corporate.evidence_calibration import EvidenceCalibratedCorporateHazardService
from services.financial_corporate.orchestrator import FinancialCorporateOrchestrator


class EvidenceAttributionTests(unittest.TestCase):
    def setUp(self):
        self.service = EvidenceCalibratedCorporateHazardService()
        self.entity = {
            "entity_id": "corp_nvidia",
            "common_name": "NVIDIA",
            "legal_name": "NVIDIA Corporation",
            "identifiers": {},
        }

    def test_short_openai_cyberattack_headline_is_not_nvidia_incident(self):
        media = {
            "matched_items": [
                {
                    "title": "Nvidia Forms AI Safety Alliance Following OpenAI Cyberattack",
                    "source_quality_weight": 0.6,
                    "freshness_weight": 0.75,
                    "signal_severity": "high",
                    "relevance": "direct",
                }
            ]
        }
        result = self.service.direct_enterprise_incident_pressure(self.entity, media)
        self.assertIsNone(result["score"])
        self.assertEqual(result["status"], "screened_no_direct_enterprise_incident")
        self.assertEqual(len(result["rejected_co_mentions"]), 1)

    def test_nvidia_confirms_own_breach_is_direct(self):
        media = {
            "matched_items": [
                {
                    "title": "NVIDIA confirms GeForce NOW data breach affecting Armenian users",
                    "source_quality_weight": 1.0,
                    "freshness_weight": 0.55,
                    "signal_severity": "high",
                    "relevance": "direct",
                }
            ]
        }
        result = self.service.direct_enterprise_incident_pressure(self.entity, media)
        self.assertEqual(result["status"], "observed")
        self.assertEqual(result["matched_count"], 1)
        self.assertGreater(result["score"], 50.0)

    def test_breach_at_company_is_direct(self):
        self.assertTrue(
            self.service._is_direct_enterprise_incident_title(
                self.entity, "Data breach at NVIDIA affects cloud gaming users"
            )
        )

    def test_supplier_breach_mention_is_not_direct(self):
        self.assertFalse(
            self.service._is_direct_enterprise_incident_title(
                self.entity, "Foxconn ransomware breach exposes files linked to NVIDIA"
            )
        )


class CorporateEvidenceConfidenceTests(unittest.TestCase):
    def test_cross_module_source_confidence_is_propagated(self):
        evidence = {
            "cross_module": {
                "evidence": {
                    "supply_chain": [{"confidence": 75.0}],
                    "geopolitical": [{"confidence": 61.5}, {"confidence": 70.0}],
                    "sanctions_compliance": [{"confidence": 83.0}],
                    "governance_operational": [{"confidence": 84.0}],
                }
            }
        }
        orchestrator = FinancialCorporateOrchestrator()
        self.assertEqual(
            orchestrator._cross_module_confidence(evidence, "supply_chain", score_present=True),
            75.0,
        )
        self.assertEqual(
            orchestrator._cross_module_confidence(evidence, "geopolitical", score_present=True),
            65.75,
        )
        self.assertEqual(
            orchestrator._cross_module_confidence(evidence, "sanctions_compliance", score_present=True),
            83.0,
        )

    def test_unproven_manual_score_does_not_get_full_confidence(self):
        orchestrator = FinancialCorporateOrchestrator()
        self.assertEqual(
            orchestrator._cross_module_confidence({}, "geopolitical", score_present=True),
            60.0,
        )


if __name__ == "__main__":
    unittest.main()
