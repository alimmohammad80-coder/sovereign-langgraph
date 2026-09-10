from services.financial_corporate.corporate_credit import CorporateCreditVulnerabilityAnalyzer
from services.financial_corporate.debt_refinancing import DebtRefinancingAnalyzer
from services.financial_corporate.sensitivity import FinancialSensitivityAnalyzer
from services.financial_corporate.trends import FinancialTrendAnalyzer


def obs(value):
    return {"value": value}


def test_debt_refinancing_uses_reported_maturities_and_buffers():
    analyzer = DebtRefinancingAnalyzer()
    result = analyzer.analyze(
        {
            "cash": obs(40),
            "long_term_debt": obs(100),
            "operating_cash_flow": obs(30),
        },
        {
            "year_1": obs(20),
            "year_2": obs(15),
            "year_3": obs(10),
            "year_4": None,
            "year_5": None,
            "thereafter": obs(55),
        },
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
        {
            "long_term_debt": obs(1_000),
            "interest_expense": obs(40),
            "operating_income": obs(200),
            "revenue": obs(2_000),
        }
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
            "long_term_debt": obs(300),
            "cash": obs(50),
            "equity": obs(200),
            "operating_income": obs(80),
            "interest_expense": obs(20),
            "operating_cash_flow": obs(70),
            "current_assets": obs(250),
            "current_liabilities": obs(150),
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
