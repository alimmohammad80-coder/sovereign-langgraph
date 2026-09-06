import unittest
from types import SimpleNamespace

from services.financial_corporate.narrative_refiner import (
    FinancialCorporateNarrativeRefiner,
    NarrativeValidationError,
)


class _FakeGateway:
    def __init__(self, payload=None, *, configured=True, error=None):
        self.payload = payload
        self.configured = configured
        self.error = error
        self.requests = []

    def available_providers(self):
        return ["NVIDIA"] if self.configured else []

    def generate(self, request):
        self.requests.append(request)
        if self.error:
            raise self.error
        return SimpleNamespace(
            provider="NVIDIA",
            model="nvidia/test",
            latency_ms=12,
            parsed_json=self.payload,
            metadata={"fallback_used": False},
        )


class FinancialCorporateNarrativeRefinerTests(unittest.TestCase):
    def setUp(self):
        self.report = {
            "entity": {"common_name": "Example Corp"},
            "assessment": {
                "risk_score": 64.8,
                "risk_level": "Elevated",
                "confidence": 72,
                "assessment_status": "complete",
                "score_authority": "integrated_snapshot",
                "ai_generated_score": False,
            },
            "bluf": "Baseline deterministic BLUF.",
            "sections": {
                "overall_assessment": {
                    "title": "Overall Assessment",
                    "claims": [
                        {
                            "claim_type": "JUDGMENT",
                            "text": "Integrated exposure remains elevated.",
                            "evidence_ids": ["ev-overall"],
                        }
                    ],
                },
                "cyber_operational": {
                    "title": "Cyber / Operational",
                    "claims": [
                        {
                            "claim_type": "FACT",
                            "text": "A supplier incident is retained as ecosystem context, not a direct company incident.",
                            "evidence_ids": ["ev-cyber"],
                        }
                    ],
                },
            },
            "evidence_registry": [
                {
                    "evidence_id": "ev-overall",
                    "source": "integrated_snapshot",
                    "title": "Integrated score",
                    "status": "observed",
                },
                {
                    "evidence_id": "ev-cyber",
                    "source": "quality-weighted cyber reporting",
                    "title": "Supplier incident involving company files",
                    "status": "observed",
                    "attribution_category": "ecosystem_incident",
                },
            ],
            "evidence_gaps": [],
            "indicators_to_watch": [],
            "key_judgments": [],
        }
        self.valid_payload = {
            "bluf": "Example Corp remains exposed primarily through the validated integrated risk picture and ecosystem context.",
            "section_summaries": {
                "overall_assessment": {
                    "text": "The integrated evidence supports an elevated operating-risk posture.",
                    "evidence_ids": ["ev-overall"],
                },
                "cyber_operational": {
                    "text": "Cyber reporting concerns a supplier context and does not establish a direct enterprise incident.",
                    "evidence_ids": ["ev-cyber"],
                },
            },
            "key_judgments": [
                {
                    "text": "The supplier cyber event should remain ecosystem exposure rather than direct victim attribution.",
                    "evidence_ids": ["ev-cyber"],
                }
            ],
            "analytic_caveats": ["Narrative synthesis does not modify deterministic scores."],
        }

    def test_accepts_grounded_overlay_without_changing_assessment(self):
        gateway = _FakeGateway(self.valid_payload)
        refined = FinancialCorporateNarrativeRefiner(gateway).refine(self.report)

        self.assertEqual(refined["narrative_refinement"]["status"], "accepted")
        self.assertEqual(refined["assessment"], self.report["assessment"])
        self.assertEqual(refined["baseline_bluf"], self.report["bluf"])
        self.assertEqual(refined["bluf"], self.valid_payload["bluf"])
        self.assertEqual(
            refined["sections"]["cyber_operational"]["narrative_summary"]["evidence_ids"],
            ["ev-cyber"],
        )
        self.assertFalse(refined["narrative_refinement"]["model_can_modify_scores"])

    def test_rejects_model_score_override(self):
        payload = dict(self.valid_payload)
        payload["risk_score"] = 12
        with self.assertRaises(NarrativeValidationError):
            FinancialCorporateNarrativeRefiner.validate_candidate(payload, self.report)

    def test_rejects_unknown_evidence_reference(self):
        payload = dict(self.valid_payload)
        payload["section_summaries"] = {
            "overall_assessment": {
                "text": "A grounded-looking but unsupported statement.",
                "evidence_ids": ["ev-invented"],
            }
        }
        with self.assertRaises(NarrativeValidationError):
            FinancialCorporateNarrativeRefiner.validate_candidate(payload, self.report)

    def test_rejects_negative_screening_as_zero_risk(self):
        payload = dict(self.valid_payload)
        payload["bluf"] = "The company has no sanctions risk."
        with self.assertRaises(NarrativeValidationError):
            FinancialCorporateNarrativeRefiner.validate_candidate(payload, self.report)

    def test_rejects_invented_event_probability(self):
        payload = dict(self.valid_payload)
        payload["bluf"] = "The probability of disruption is 72% over the next 90 days."
        with self.assertRaises(NarrativeValidationError):
            FinancialCorporateNarrativeRefiner.validate_candidate(payload, self.report)

    def test_provider_failure_falls_back_to_deterministic_report(self):
        refined = FinancialCorporateNarrativeRefiner(
            _FakeGateway(error=RuntimeError("provider unavailable"))
        ).refine(self.report)

        self.assertEqual(refined["bluf"], self.report["bluf"])
        self.assertEqual(refined["assessment"], self.report["assessment"])
        self.assertEqual(refined["narrative_refinement"]["status"], "fallback")

    def test_no_provider_falls_back_without_model_call(self):
        gateway = _FakeGateway(configured=False)
        refined = FinancialCorporateNarrativeRefiner(gateway).refine(self.report)
        self.assertEqual(refined["narrative_refinement"]["status"], "fallback")
        self.assertEqual(refined["narrative_refinement"]["reason"], "no_configured_ai_provider")
        self.assertEqual(gateway.requests, [])


if __name__ == "__main__":
    unittest.main()
