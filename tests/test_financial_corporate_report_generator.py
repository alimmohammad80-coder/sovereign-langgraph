from __future__ import annotations

import unittest

from services.financial_corporate.report_generator import (
    FinancialCorporateReportGenerator,
    ReportOptions,
)


class FinancialCorporateReportGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.generator = FinancialCorporateReportGenerator()
        self.snapshot = {
            "entity": {
                "entity_id": "corp_nvidia",
                "legal_name": "NVIDIA Corporation",
                "common_name": "NVIDIA",
                "tickers": ["NVDA"],
            },
            "overall": {
                "overall_risk_score": 33.57,
                "risk_level": "Low",
                "assessment_status": "complete",
                "confidence_score": 85.31,
                "methodology": "deterministic_weighted_multifactor_v2_missing_aware",
                "dimensions": {
                    "financial_resilience": 0.26,
                    "market_stress": 27.13,
                    "supply_chain": 56.58,
                    "geopolitical": 66.16,
                    "sanctions_compliance": 18.28,
                    "governance_operational": 47.08,
                },
                "dimension_confidence": {
                    "financial_resilience": 100.0,
                    "market_stress": 100.0,
                    "supply_chain": 75.0,
                    "geopolitical": 65.75,
                    "sanctions_compliance": 83.0,
                    "governance_operational": 81.7,
                },
                "top_drivers": [
                    {
                        "dimension": "supply_chain",
                        "score": 56.58,
                        "weighted_contribution": 11.316,
                    },
                    {
                        "dimension": "geopolitical",
                        "score": 66.16,
                        "weighted_contribution": 10.586,
                    },
                    {
                        "dimension": "governance_operational",
                        "score": 47.08,
                        "weighted_contribution": 4.708,
                    },
                ],
                "missing_dimensions": [],
            },
            "distress": {
                "distress_score": 4.26,
                "distress_level": "Low",
                "confidence_score": 100.0,
            },
            "fundamentals": {
                "financial_resilience_risk_score": 0.26,
                "evidence_coverage": 100.0,
                "methodology": "fundamental_ratio_risk_v1",
                "ratios": {
                    "current_ratio": 3.9053,
                    "debt_to_equity": 0.0475,
                    "net_margin": 0.556,
                },
            },
            "market_credit": {
                "market_credit_stress_score": 27.13,
                "confidence_score": 100.0,
                "evidence_coverage": 100.0,
                "methodology": "confidence_weighted_market_credit_v2_coverage_aware",
                "components": {},
            },
            "evidence": {
                "sec": {
                    "cik": "0001045810",
                    "title": "NVIDIA CORP",
                    "source": "SEC EDGAR/XBRL",
                    "source_url": "https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json",
                },
                "cross_module": {
                    "evidence": {
                        "supply_chain": [
                            {
                                "source_entity_id": "country:TWN",
                                "relationship_type": "semiconductor_supply_chain",
                                "source_module": "Supply Chain Intelligence",
                                "structural_exposure": 0.92,
                                "hazard_intensity": 82.0,
                                "confidence": 75.0,
                                "risk_contribution": 56.58,
                            }
                        ],
                        "geopolitical": [
                            {
                                "source_entity_id": "conflict:TWN",
                                "relationship_type": "dynamic_conflict_hazard_exposure",
                                "source_module": "Conflict Forecasting",
                                "structural_exposure": 0.92,
                                "hazard_intensity": 82.0,
                                "confidence": 70.0,
                                "risk_contribution": 52.81,
                            }
                        ],
                        "sanctions_compliance": [
                            {
                                "source_entity_id": "trade-control:company-policy-pressure",
                                "relationship_type": "company_trade_control_policy_pressure",
                                "source_module": "Sanctions / Trade Intelligence",
                                "hazard_intensity": 22.03,
                                "confidence": 83.0,
                                "risk_contribution": 18.28,
                            }
                        ],
                        "governance_operational": [
                            {
                                "source_entity_id": "operational:company-semantic-composite",
                                "relationship_type": "company_governance_operational_pressure",
                                "source_module": "Cyber & Information Operations",
                                "hazard_intensity": 57.63,
                                "confidence": 81.7,
                                "risk_contribution": 47.08,
                            }
                        ],
                    }
                },
                "dynamic_hazards": {
                    "country_hazards": {
                        "TWN": {
                            "status": "observed",
                            "score": 50.0,
                            "confidence": 61.5,
                            "source": "Country Intelligence",
                            "freshness": {
                                "age_days": 57.3,
                                "freshness_status": "aging",
                            },
                        }
                    },
                    "conflict_hazards": {
                        "TWN": {
                            "status": "observed",
                            "score": 82.0,
                            "confidence": 70.0,
                            "source": "Conflict Forecasting",
                            "country": "Taiwan",
                        }
                    },
                    "sanctions_screening": {
                        "status": "screened_no_direct_match",
                        "match": False,
                        "score": None,
                        "source": "OFAC Sanctions List Service",
                        "source_url": "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.CSV",
                    },
                    "trade_control_pressure": {
                        "status": "observed",
                        "score": 26.54,
                        "confidence": 83.0,
                        "signal_buckets": {
                            "direct_sanctions_designation": 0,
                            "compliance_enforcement_exposure": 1,
                            "direct_export_control_exposure": 2,
                            "downstream_diversion_risk": 2,
                            "policy_context": 1,
                        },
                        "matched_items": [
                            {
                                "title": "Nvidia chips reached a downstream restricted user",
                                "source": "Example News",
                                "published": "2026-07-27",
                                "link": "https://example.com/diversion",
                                "attribution_category": "downstream_diversion_risk",
                                "semantic_weight": 0.35,
                            }
                        ],
                    },
                    "sec_material_cyber_disclosure": {
                        "status": "screened_no_recent_item_1_05",
                        "source": "SEC EDGAR submissions",
                        "source_url": "https://data.sec.gov/submissions/CIK0001045810.json",
                    },
                    "direct_enterprise_cyber_incident": {
                        "status": "observed",
                        "score": 60.1,
                        "confidence": 80.0,
                        "matched_count": 1,
                        "matched_items": [
                            {
                                "title": "NVIDIA confirms service data breach",
                                "source": "BleepingComputer",
                                "published": "2026-05-08",
                                "link": "https://example.com/nvidia-breach",
                                "attribution_category": "direct_enterprise_incident",
                            }
                        ],
                    },
                    "cyber_nvd_pressure": {
                        "status": "observed",
                        "score": 77.12,
                        "confidence": 90.0,
                        "source": "NIST National Vulnerability Database",
                        "source_url": "https://services.nvd.nist.gov/rest/json/cves/2.0",
                        "matched_count": 50,
                        "max_cvss_base_score": 9.8,
                        "average_cvss_base_score": 7.48,
                    },
                    "cyber_media_pressure": {
                        "status": "observed",
                        "score": 39.48,
                        "confidence": 82.15,
                        "matched_items": [
                            {
                                "title": "Supplier breach mentions Nvidia files",
                                "source": "Example Cyber News",
                                "published": "2026-05-12",
                                "link": "https://example.com/supplier",
                                "attribution_category": "ecosystem_incident",
                            }
                        ],
                    },
                },
                "collection_errors": [],
            },
            "methodology": "financial_corporate_integrated_snapshot_v4_evidence_confidence",
            "ai_generated_score": False,
        }

    def test_preserves_authoritative_score(self):
        report = self.generator.generate(self.snapshot)
        self.assertEqual(report["assessment"]["risk_score"], 33.57)
        self.assertEqual(report["assessment"]["risk_level"], "Low")
        self.assertFalse(report["assessment"]["ai_generated_score"])
        self.assertEqual(report["assessment"]["score_authority"], "integrated_snapshot")

    def test_all_claims_have_valid_evidence(self):
        report = self.generator.generate(self.snapshot)
        self.assertEqual(report["claim_validation"]["status"], "pass")
        registry = {item["evidence_id"] for item in report["evidence_registry"]}
        for section in report["sections"].values():
            for claim in section["claims"]:
                self.assertTrue(claim["evidence_ids"])
                self.assertTrue(set(claim["evidence_ids"]).issubset(registry))

    def test_negative_ofac_screening_is_not_zero_risk(self):
        report = self.generator.generate(self.snapshot)
        text = report["sections"]["sanctions_trade"]["summary"].lower()
        self.assertIn("does not establish zero sanctions", text)
        self.assertNotIn("no sanctions risk", text)

    def test_downstream_diversion_is_not_company_misconduct(self):
        report = self.generator.generate(self.snapshot)
        text = report["sections"]["sanctions_trade"]["summary"].lower()
        self.assertIn("not evidence of company misconduct", text)

    def test_product_security_remains_separate_from_enterprise_incident(self):
        report = self.generator.generate(self.snapshot)
        claims = report["sections"]["cyber_operational"]["claims"]
        enterprise = [c for c in claims if "victim-attributed" in c["text"].lower()]
        product = [c for c in claims if "nvd product-security" in c["text"].lower()]
        self.assertEqual(len(enterprise), 1)
        self.assertEqual(len(product), 1)
        self.assertNotEqual(set(enterprise[0]["evidence_ids"]), set(product[0]["evidence_ids"]))

    def test_aging_country_evidence_is_surfaced(self):
        report = self.generator.generate(self.snapshot)
        aging = [gap for gap in report["evidence_gaps"] if gap.get("type") == "aging_evidence"]
        self.assertEqual(len(aging), 1)
        self.assertEqual(aging[0]["source"], "country:TWN")

    def test_forecasts_have_horizon_and_are_not_probabilities(self):
        report = self.generator.generate(
            self.snapshot,
            ReportOptions(forecast_horizons=("30d", "90d", "180d")),
        )
        claims = report["sections"]["outlook"]["claims"]
        self.assertEqual([claim["horizon"] for claim in claims], ["30d", "90d", "180d"])
        self.assertTrue(all("not a calibrated event probability" in claim["text"] for claim in claims))

    def test_renderers_include_sources(self):
        report = self.generator.generate(self.snapshot)
        markdown = self.generator.render_markdown(report)
        html = self.generator.render_html(report)
        self.assertIn("## Notes / Sources", markdown)
        self.assertIn("SEC EDGAR/XBRL", markdown)
        self.assertIn("<h1>", html)
        self.assertIn("Notes / Sources", html)

    def test_missing_dimension_remains_explicit(self):
        snapshot = dict(self.snapshot)
        snapshot["overall"] = dict(self.snapshot["overall"])
        snapshot["overall"]["missing_dimensions"] = ["sanctions_compliance"]
        snapshot["overall"]["assessment_status"] = "partial"
        report = self.generator.generate(snapshot)
        gaps = [gap for gap in report["evidence_gaps"] if gap.get("type") == "missing_dimension"]
        self.assertEqual(gaps[0]["dimension"], "sanctions_compliance")
        self.assertEqual(report["assessment"]["assessment_status"], "partial")


if __name__ == "__main__":
    unittest.main()
