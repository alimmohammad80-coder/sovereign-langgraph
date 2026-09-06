from unittest.mock import patch

from services.financial_corporate.report_generator import (
    FinancialCorporateReportGenerator,
    ReportOptions,
)
from services.financial_corporate.report_generator_hardened import (
    HardenedFinancialCorporateReportGenerator,
)


def test_trade_collection_error_does_not_emit_zero_signal_claim():
    generator = HardenedFinancialCorporateReportGenerator()
    base_sections = {
        "sanctions_trade": {
            "title": "Sanctions & Trade Controls",
            "summary": "integrated trade signal counts",
            "claims": [
                {"claim_type": "FACT", "text": "integrated", "evidence_ids": ["model:integrated_risk"]},
                {"claim_type": "JUDGMENT", "text": "0 direct export-control signals", "evidence_ids": ["model:integrated_risk"]},
            ],
        },
        "cyber_operational": {"title": "Cyber", "summary": "", "claims": []},
    }
    snapshot = {
        "evidence": {
            "dynamic_hazards": {
                "trade_control_pressure": {"status": "error", "error": "news unavailable"}
            }
        }
    }
    with patch.object(FinancialCorporateReportGenerator, "_build_sections", return_value=base_sections):
        sections = generator._build_sections(snapshot, {}, ReportOptions())
    assert len(sections["sanctions_trade"]["claims"]) == 1
    assert "0 direct export-control" not in sections["sanctions_trade"]["summary"]


def test_nvd_collection_error_does_not_emit_zero_vulnerability_fact():
    generator = HardenedFinancialCorporateReportGenerator()
    base_sections = {
        "sanctions_trade": {"title": "Sanctions", "summary": "", "claims": []},
        "cyber_operational": {
            "title": "Cyber",
            "summary": "operational 0 vulnerabilities",
            "claims": [
                {"claim_type": "JUDGMENT", "text": "operational", "evidence_ids": ["model:integrated_risk"]},
                {"claim_type": "FACT", "text": "0 recently published vulnerabilities", "evidence_ids": ["nvd:product_security"]},
            ],
        },
    }
    snapshot = {
        "evidence": {
            "dynamic_hazards": {
                "cyber_nvd_pressure": {"status": "error", "error": "NVD timeout"}
            }
        }
    }
    with patch.object(FinancialCorporateReportGenerator, "_build_sections", return_value=base_sections):
        sections = generator._build_sections(snapshot, {}, ReportOptions())
    claims = sections["cyber_operational"]["claims"]
    assert len(claims) == 1
    assert claims[0]["claim_type"] == "JUDGMENT"
    assert "vulnerabilities" not in sections["cyber_operational"]["summary"]


def test_collector_errors_become_material_evidence_gaps():
    generator = HardenedFinancialCorporateReportGenerator()
    snapshot = {
        "overall": {},
        "evidence": {
            "dynamic_hazards": {
                "trade_control_pressure": {"status": "error", "error": "news unavailable"},
                "cyber_nvd_pressure": {"status": "error", "error": "NVD timeout"},
            }
        },
    }
    gaps = generator._evidence_gaps(snapshot)
    sources = {gap.get("source") for gap in gaps if gap.get("type") == "collection_error"}
    assert "trade_control_pressure" in sources
    assert "cyber_nvd_pressure" in sources
    assert all(
        gap.get("severity") == "material"
        for gap in gaps
        if gap.get("source") in {"trade_control_pressure", "cyber_nvd_pressure"}
    )
