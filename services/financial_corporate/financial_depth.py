from __future__ import annotations

from typing import Any, Dict

from .corporate_credit import CorporateCreditVulnerabilityAnalyzer
from .debt_refinancing import DebtRefinancingAnalyzer
from .financial_forecast import FinancialRiskForecastEngine
from .market_credit import MarketCreditIntelligenceService
from .resilience_calibration import FinancialResilienceCalibrationEngine
from .sec_edgar import SECEdgarCollector
from .sec_financial_depth import SECFinancialDepthCollector
from .sensitivity import FinancialSensitivityAnalyzer
from .trends import FinancialTrendAnalyzer


class FinancialDepthService:
    """Build deeper financial evidence and guarded calibrated resilience outputs."""

    def __init__(self) -> None:
        self.sec = SECEdgarCollector()
        self.sec_depth = SECFinancialDepthCollector(self.sec)
        self.market_credit = MarketCreditIntelligenceService()
        self.debt_refinancing = DebtRefinancingAnalyzer()
        self.sensitivity = FinancialSensitivityAnalyzer()
        self.trends = FinancialTrendAnalyzer()
        self.corporate_credit = CorporateCreditVulnerabilityAnalyzer()
        self.resilience_calibration = FinancialResilienceCalibrationEngine()
        self.forecast_engine = FinancialRiskForecastEngine()

    def collect(self, symbol: str) -> Dict[str, Any]:
        normalized_symbol = symbol.strip().upper()
        errors = []
        resolved = self.sec.resolve_ticker(normalized_symbol)
        if not resolved:
            return {
                "symbol": normalized_symbol,
                "assessment_status": "insufficient_evidence",
                "errors": [{"component": "sec_edgar", "error": f"Ticker {normalized_symbol} not found in SEC index"}],
                "ai_generated_score": False,
            }

        observations: Dict[str, Any] = {}
        depth_raw: Dict[str, Any] = {}
        fundamentals = None
        try:
            facts = self.sec.fetch_company_facts(resolved["cik"])
            observations = facts.get("financial_observations") or {}
            fundamentals = self._fundamentals_from_observations(observations)
        except Exception as exc:
            errors.append({"component": "sec_financial_observations", "error": str(exc)})

        try:
            depth_raw = self.sec_depth.collect(resolved["cik"])
        except Exception as exc:
            errors.append({"component": "sec_financial_depth", "error": str(exc)})

        credit_analysis = None
        try:
            credit_analysis = self.market_credit.credit_snapshot().get("analysis")
        except Exception as exc:
            errors.append({"component": "credit_conditions", "error": str(exc)})

        market_analysis = None
        try:
            market_analysis = self.market_credit.company_market_snapshot(normalized_symbol).get("analysis")
        except Exception as exc:
            errors.append({"component": "equity_market", "error": str(exc)})

        debt = self.debt_refinancing.analyze(observations, depth_raw.get("debt_maturities") or {}, credit_analysis)
        sensitivity = self.sensitivity.analyze(observations)
        trends = self.trends.analyze(depth_raw.get("financial_history") or {})
        company_credit = self.corporate_credit.analyze(observations, debt, credit_analysis)
        calibrated_resilience = self.resilience_calibration.calibrate(
            fundamentals=fundamentals,
            debt_refinancing=debt,
            credit_vulnerability=company_credit,
            financial_trends=trends,
        )

        observed_sections = sum(
            1
            for status in (
                debt.get("assessment_status"),
                sensitivity.get("rate_sensitivity", {}).get("status"),
                trends.get("assessment_status"),
                company_credit.get("assessment_status"),
            )
            if status not in {None, "insufficient_evidence"}
        )

        return {
            "symbol": normalized_symbol,
            "entity": {"ticker": resolved.get("ticker"), "cik": resolved.get("cik"), "legal_name": resolved.get("title")},
            "assessment_status": "complete" if observed_sections == 4 and not errors else ("partial" if observed_sections else "insufficient_evidence"),
            "fundamentals": fundamentals,
            "debt_refinancing": debt,
            "credit_vulnerability": company_credit,
            "sensitivity": sensitivity,
            "financial_trends": trends,
            "calibrated_financial_resilience": calibrated_resilience,
            "market_analysis": market_analysis,
            "source_evidence": {
                "sec": {
                    "source_url": depth_raw.get("source_url"),
                    "maturity_buckets_observed": depth_raw.get("maturity_buckets_observed", 0),
                    "history_metrics_observed": depth_raw.get("history_metrics_observed", 0),
                },
                "credit_conditions": credit_analysis,
            },
            "errors": errors,
            "score_policy": "guarded_calibration_available_not_yet_authoritative_topline",
            "ai_generated_score": False,
        }

    @staticmethod
    def _fundamentals_from_observations(observations: Dict[str, Any]) -> Dict[str, Any]:
        from .fundamentals import CorporateFundamentalsAnalyzer
        return CorporateFundamentalsAnalyzer().analyze(observations)
