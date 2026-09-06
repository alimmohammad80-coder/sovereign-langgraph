import unittest

from services.financial_corporate.credit_conditions import CreditConditionsAnalyzer
from services.financial_corporate.market_credit import MarketCreditIntelligenceService
from services.financial_corporate.market_data import MarketStressAnalyzer


class MarketStressAnalyzerTests(unittest.TestCase):
    def test_falling_volatile_prices_generate_stress(self):
        observations = []
        price = 100.0
        for index in range(100):
            price *= 0.995 if index % 2 == 0 else 0.985
            observations.append({"date": f"2026-01-{(index % 28) + 1:02d}", "close": price})
        result = MarketStressAnalyzer().analyze({"observations": observations})
        self.assertGreater(result["market_stress_score"], 25)
        self.assertEqual(result["confidence_score"], 100.0)
        self.assertEqual(result["assessment_status"], "observed")
        self.assertFalse(result["ai_generated_score"])

    def test_insufficient_history_is_missing_not_neutral_fifty(self):
        result = MarketStressAnalyzer().analyze({"observations": [{"close": 100}, {"close": 99}]})
        self.assertIsNone(result["market_stress_score"])
        self.assertEqual(result["confidence_score"], 0.0)
        self.assertEqual(result["assessment_status"], "missing")
        self.assertEqual(result["reason"], "insufficient_price_history")


class CreditConditionsAnalyzerTests(unittest.TestCase):
    @staticmethod
    def _series(values):
        return {"observations": [{"date": str(index), "value": value} for index, value in enumerate(values)]}

    def test_credit_stress_uses_available_series(self):
        payload = {
            "series": {
                "baa_10y_spread": self._series([1.5] * 25 + [3.5]),
                "aaa_10y_spread": self._series([1.5] * 26),
                "ten_year_minus_fed_funds": self._series([-1.0] * 26),
                "effective_fed_funds": self._series([5.0] * 26),
            }
        }
        result = CreditConditionsAnalyzer().analyze(payload)
        self.assertGreater(result["credit_conditions_score"], 30)
        self.assertGreater(result["confidence_score"], 50)
        self.assertFalse(result["ai_generated_score"])


class MarketCreditAggregationTests(unittest.TestCase):
    def test_confidence_weighted_combination(self):
        service = MarketCreditIntelligenceService()
        result = service.combined_score(
            market_analysis={"market_stress_score": 80, "confidence_score": 100},
            credit_analysis={"credit_conditions_score": 40, "confidence_score": 100},
        )
        self.assertEqual(result["market_credit_stress_score"], 66.0)
        self.assertEqual(result["confidence_score"], 100.0)
        self.assertFalse(result["ai_generated_score"])

    def test_missing_equity_does_not_inject_neutral_fifty(self):
        service = MarketCreditIntelligenceService()
        result = service.combined_score(
            market_analysis={"market_stress_score": None, "confidence_score": 0.0, "assessment_status": "missing"},
            credit_analysis={"credit_conditions_score": 20, "confidence_score": 100},
        )
        self.assertEqual(result["market_credit_stress_score"], 20.0)
        self.assertNotIn("equity_market", result["components"])
        self.assertIn("credit_conditions", result["components"])


if __name__ == "__main__":
    unittest.main()
