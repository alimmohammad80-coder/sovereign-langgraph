import unittest

from services.financial_corporate.fundamentals import CorporateFundamentalsAnalyzer
from services.financial_corporate.gleif import GLEIFCollector
from services.financial_corporate.sec_edgar import SECEdgarCollector


class SECEdgarCollectorTests(unittest.TestCase):
    def test_normalize_cik(self):
        self.assertEqual(SECEdgarCollector.normalize_cik(320193), "0000320193")
        self.assertEqual(SECEdgarCollector.normalize_cik("CIK320193"), "0000320193")

    def test_normalize_submissions(self):
        raw = {
            "cik": 320193,
            "name": "Apple Inc.",
            "tickers": ["AAPL"],
            "exchanges": ["Nasdaq"],
            "filings": {
                "recent": {
                    "form": ["10-K"],
                    "accessionNumber": ["0000320193-26-000001"],
                    "filingDate": ["2026-01-01"],
                    "primaryDocument": ["aapl-2026.htm"],
                }
            },
        }
        normalized = SECEdgarCollector.normalize_submissions(raw)
        self.assertEqual(normalized["identity"]["cik"], "0000320193")
        self.assertEqual(normalized["identity"]["tickers"], ["AAPL"])
        self.assertEqual(normalized["recent_filings"][0]["form"], "10-K")

    def test_normalize_company_facts(self):
        raw = {
            "cik": 1,
            "entityName": "Example Corp",
            "facts": {
                "us-gaap": {
                    "Assets": {
                        "label": "Assets",
                        "units": {
                            "USD": [
                                {"val": 1000, "end": "2025-12-31", "filed": "2026-02-01", "form": "10-K"}
                            ]
                        },
                    }
                }
            },
        }
        normalized = SECEdgarCollector.normalize_company_facts(raw)
        self.assertEqual(normalized["financial_observations"]["assets"]["value"], 1000)


class GLEIFCollectorTests(unittest.TestCase):
    def test_normalize_record(self):
        item = {
            "id": "TESTLEI123",
            "attributes": {
                "lei": "TESTLEI123",
                "entity": {
                    "legalName": {"name": "Example Holdings"},
                    "jurisdiction": "US-DE",
                    "status": "ACTIVE",
                    "legalAddress": {"country": "US", "city": "Wilmington"},
                },
                "registration": {"status": "ISSUED"},
            },
        }
        normalized = GLEIFCollector._normalize_record(item)
        self.assertEqual(normalized["lei"], "TESTLEI123")
        self.assertEqual(normalized["legal_name"], "Example Holdings")
        self.assertEqual(normalized["legal_address"]["country"], "US")


class CorporateFundamentalsAnalyzerTests(unittest.TestCase):
    def test_analyze_financial_observations(self):
        observations = {
            "assets": {"value": 1000},
            "liabilities": {"value": 500},
            "equity": {"value": 500},
            "cash": {"value": 200},
            "current_assets": {"value": 400},
            "current_liabilities": {"value": 200},
            "long_term_debt": {"value": 100},
            "revenue": {"value": 1000},
            "net_income": {"value": 150},
            "operating_income": {"value": 200},
            "interest_expense": {"value": 20},
            "operating_cash_flow": {"value": 250},
        }
        result = CorporateFundamentalsAnalyzer().analyze(observations)
        self.assertEqual(result["ratios"]["current_ratio"], 2.0)
        self.assertEqual(result["ratios"]["interest_coverage"], 10.0)
        self.assertGreater(result["evidence_coverage"], 0)
        self.assertFalse(result["financial_resilience_risk_score"] < 0)
        self.assertFalse(result["financial_resilience_risk_score"] > 100)


if __name__ == "__main__":
    unittest.main()
