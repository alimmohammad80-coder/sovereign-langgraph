import json

import pytest

from app.services.supply_chain_report_generator import (
    SupplyChainReportGenerationError,
    _compact_value,
    _extract_json,
    _validate_report,
)


def _payload(analysis_words: int = 350, bluf_words: int = 80):
    return {
        "bluf": " ".join(["judgment"] * bluf_words),
        "complete_analysis": " ".join(["assessment"] * analysis_words),
        "confidence": "Moderate",
        "forecast": {
            "7_day": "Near-term monitoring continues.",
            "30_day": "Exposure remains elevated.",
            "90_day": "Mitigation may reduce concentration risk.",
        },
        "drivers": ["Concentration risk"],
        "sources": [{"name": "Live disruption feed", "title": "Observed signal"}],
    }


def test_validates_publication_length_and_metadata():
    report = _validate_report(_payload())

    assert report["analysis_word_count"] == 350
    assert report["confidence"] == "Moderate"
    assert report["sources"][0]["name"] == "Live disruption feed"


@pytest.mark.parametrize("word_count", [0, 299, 501])
def test_rejects_reports_outside_required_length(word_count):
    with pytest.raises(SupplyChainReportGenerationError):
        _validate_report(_payload(analysis_words=word_count))


def test_extracts_json_from_fenced_model_output():
    payload = _payload()
    fence = chr(96) * 3
    parsed = _extract_json(f"{fence}json\n{json.dumps(payload)}\n{fence}")

    assert parsed["confidence"] == "Moderate"


def test_compacts_large_context_without_losing_subject():
    context = {
        "companies": [
            {
                "entity_name": "TSMC",
                "company_profile": {"sector": "Semiconductors", "risk_score": 65},
                "signals": [{"title": f"Signal {index}"} for index in range(25)],
            }
        ]
    }

    compact = _compact_value(context)

    assert compact["companies"][0]["entity_name"] == "TSMC"
    assert len(compact["companies"][0]["signals"]) == 10
