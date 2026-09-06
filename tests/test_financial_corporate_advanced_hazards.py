import unittest
from datetime import datetime, timedelta, timezone

from services.financial_corporate.advanced_hazards import AdvancedCorporateHazardService


class _BaseStub:
    def enrich(self, *, company_entity_id, entity, edges):
        return {
            "edges": [
                {
                    "source_entity_id": "country:TWN",
                    "target_entity_id": company_entity_id,
                    "relationship_type": "dynamic_country_hazard_exposure",
                    "weight": 0.92,
                    "source_module": "Country Intelligence",
                    "confidence": 82.0,
                    "evidence": {
                        "country_hazard": {
                            "status": "observed",
                            "score": 50.0,
                            "confidence": 82.0,
                            "created_at": (datetime.now(timezone.utc) - timedelta(days=70)).isoformat(),
                        }
                    },
                },
                {
                    "source_entity_id": "commodity:8542",
                    "target_entity_id": "corp_apple",
                    "relationship_type": "commodity_dependency",
                    "weight": 0.42,
                    "source_module": "Supply Chain Intelligence",
                    "confidence": 75.0,
                    "evidence": {},
                },
            ],
            "country_hazards": {
                "TWN": {
                    "status": "observed",
                    "score": 50.0,
                    "confidence": 82.0,
                    "created_at": (datetime.now(timezone.utc) - timedelta(days=70)).isoformat(),
                }
            },
            "conflict_hazards": {},
            "sanctions_screening": {"status": "screened_no_direct_match", "score": None},
            "cyber_screening": {"status": "screened_no_company_match", "score": None},
            "added_edge_count": 0,
        }


class _NoNetworkAdvanced(AdvancedCorporateHazardService):
    def trade_control_pressure(self, entity):
        return {"status": "screened_no_material_signal", "score": None}

    def nvd_company_pressure(self, entity):
        return {"status": "screened_no_recent_match", "score": None}

    def cyber_media_pressure(self, entity):
        return {"status": "screened_no_material_signal", "score": None}


class AdvancedCorporateHazardTests(unittest.TestCase):
    def test_freshness_decay_reduces_stale_confidence(self):
        observed_at = (datetime.now(timezone.utc) - timedelta(days=70)).isoformat()
        result = AdvancedCorporateHazardService.freshness(observed_at, 82.0)
        self.assertEqual(result["freshness_status"], "stale")
        self.assertLess(result["effective_confidence"], 82.0)
        self.assertGreater(result["effective_confidence"], 0.0)

    def test_enrichment_filters_unrelated_company_edges(self):
        service = _NoNetworkAdvanced(base=_BaseStub())
        result = service.enrich(
            company_entity_id="corp_nvidia",
            entity={"entity_id": "corp_nvidia", "common_name": "NVIDIA"},
            edges=[],
        )
        self.assertTrue(result["edges"])
        self.assertTrue(all(edge["target_entity_id"] == "corp_nvidia" for edge in result["edges"]))
        self.assertEqual(result["edge_scope"], "requested_company_only")
        self.assertEqual(result["country_hazards"]["TWN"]["freshness"]["freshness_status"], "stale")
        self.assertLess(result["edges"][0]["confidence"], 82.0)


if __name__ == "__main__":
    unittest.main()
