from services.financial_corporate.corporate_credit import CorporateCreditVulnerabilityAnalyzer
from services.financial_corporate.debt_refinancing import DebtRefinancingAnalyzer
from services.financial_corporate.financial_forecast import FinancialRiskForecastEngine
from services.financial_corporate.resilience_calibration import FinancialResilienceCalibrationEngine
from services.financial_corporate.sector_calibration import SectorRelativeCalibrationEngine
from services.financial_corporate.sensitivity import FinancialSensitivityAnalyzer
from services.financial_corporate.trends import FinancialTrendAnalyzer


def obs(value):
    return {"value": value}


def test_debt_refinancing_uses_reported_maturities_and_buffers():
    analyzer = DebtRefinancingAnalyzer()
    result = analyzer.analyze(
        {"cash": obs(40), "long_term_debt": obs(100), "operating_cash_flow": obs(30)},
        {"year_1": obs(20), "year_2": obs(15), "year_3": obs(10), "year_4": None, "year_5": None, "thereafter": obs(55)},
        {"credit_conditions_score": 60},
    )
    assert result["refinancing_risk_score"] is not None
    assert result["metrics"]["near_term_maturities"] == 35
    assert result["metrics"]["cash_to_near_term_maturities"] > 1
    assert result["ai_generated_score"] is False


def test_debt_refinancing_missing_data_is_unknown_not_neutral():
    result = DebtRefinancingAnalyzer().analyze({}, {}, None)
    assert result["refinancing_risk_score"] is None
    assert result["assessment_status"] == "insufficient_evidence"
    assert result["evidence_coverage"] == 0


def test_rate_sensitivity_calculates_incremental_interest():
    result = FinancialSensitivityAnalyzer().analyze(
        {"long_term_debt": obs(1_000), "interest_expense": obs(40), "operating_income": obs(200), "revenue": obs(2_000)}
    )
    scenarios = result["rate_sensitivity"]["scenarios"]
    assert scenarios[0]["shock_bps"] == 100
    assert scenarios[0]["incremental_interest_expense"] == 10
    assert result["fx_sensitivity"]["status"] == "insufficient_evidence"


def test_financial_trends_detect_material_deterioration():
    history = {
        "revenue": [
            {"period_end": "2024-12-31", "filed": "2025-02-01", "value": 100},
            {"period_end": "2025-12-31", "filed": "2026-02-01", "value": 80},
        ],
        "net_income": [
            {"period_end": "2024-12-31", "filed": "2025-02-01", "value": 20},
            {"period_end": "2025-12-31", "filed": "2026-02-01", "value": 10},
        ],
        "operating_cash_flow": [],
        "long_term_debt": [],
    }
    result = FinancialTrendAnalyzer().analyze(history)
    types = {item["type"] for item in result["signals"]}
    assert "revenue_contraction" in types
    assert "earnings_deterioration" in types


def test_company_credit_is_company_specific_and_missing_aware():
    analyzer = CorporateCreditVulnerabilityAnalyzer()
    result = analyzer.analyze(
        {
            "long_term_debt": obs(300), "cash": obs(50), "equity": obs(200), "operating_income": obs(80),
            "interest_expense": obs(20), "operating_cash_flow": obs(70), "current_assets": obs(250), "current_liabilities": obs(150),
        },
        {"refinancing_risk_score": 45},
        {"credit_conditions_score": 55},
    )
    assert result["credit_vulnerability_score"] is not None
    assert "leverage" in result["components"]
    assert "refinancing" in result["components"]
    assert result["ai_generated_score"] is False
    missing = analyzer.analyze({}, {}, {})
    assert missing["credit_vulnerability_score"] is None
    assert missing["assessment_status"] == "insufficient_evidence"


def test_sector_calibration_requires_real_peer_cohort():
    engine = SectorRelativeCalibrationEngine()
    insufficient = engine.calibrate(company_metrics={"debt_to_equity": 1.2}, peer_metrics=[{"debt_to_equity": 1.0}] * 4, sector_key="3571")
    assert insufficient["sector_relative_risk_score"] is None
    assert insufficient["assessment_status"] == "insufficient_evidence"

    peers = [{"debt_to_equity": x} for x in (0.4, 0.6, 0.8, 1.0, 1.2, 1.4)]
    observed = engine.calibrate(company_metrics={"debt_to_equity": 1.3}, peer_metrics=peers, sector_key="3571")
    assert observed["sector_relative_risk_score"] is not None
    assert observed["comparisons"]["debt_to_equity"]["peer_count"] == 6


def test_resilience_calibration_keeps_fundamentals_anchor_and_caps_delta():
    result = FinancialResilienceCalibrationEngine().calibrate(
        fundamentals={"financial_resilience_risk_score": 30, "evidence_coverage": 100},
        debt_refinancing={"refinancing_risk_score": 100, "confidence_score": 100},
        credit_vulnerability={"credit_vulnerability_score": 100, "confidence_score": 100},
        financial_trends={"trend_risk_score": 100, "confidence_score": 100},
        sector_relative={"sector_relative_risk_score": 100, "confidence_score": 100},
    )
    assert result["financial_resilience_risk_score"] <= 45
    assert result["score_delta"] <= 15
    assert result["ai_generated_score"] is False


def test_forecast_is_directional_not_probability_and_confidence_damped():
    engine = FinancialRiskForecastEngine()
    result = engine.forecast(
        current_risk_score=50,
        confidence_score=60,
        market_stress_score=80,
        refinancing_risk_score=75,
        credit_vulnerability_score=70,
        trend_risk_score=80,
        supply_chain_risk=65,
        geopolitical_risk=60,
    )
    assert result["probability_forecast"] is False
    assert result["horizons"]["180d"]["risk_score"] > result["horizons"]["30d"]["risk_score"]
    assert result["horizons"]["180d"]["direction"] == "deteriorating"
