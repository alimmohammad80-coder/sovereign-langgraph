from routes.financial_history import _history_point


def test_history_point_extracts_dimension_scores_and_explanation():
    row = {
        "id": "snap-1",
        "captured_at": "2026-09-10T12:00:00+00:00",
        "risk_score": 32,
        "risk_level": "Low",
        "confidence_score": 64,
        "methodology": "financial_risk_command_v2_calibrated_resilience",
        "snapshot_json": {
            "dimensions": [
                {"key": "financial_resilience", "score": 8},
                {"key": "supply_chain", "score": 57},
                {"key": "geopolitical", "score": 63},
            ],
            "explanation": {
                "largest_pressure": {"label": "Geopolitical"},
                "strongest_offset": {"label": "Financial Resilience"},
            },
        },
    }

    point = _history_point(row)

    assert point["risk_score"] == 32.0
    assert point["dimensions"]["financial_resilience"] == 8.0
    assert point["dimensions"]["supply_chain"] == 57.0
    assert point["dimensions"]["geopolitical"] == 63.0
    assert point["dimensions"]["market_stress"] is None
    assert point["largest_pressure"] == "Geopolitical"
    assert point["strongest_offset"] == "Financial Resilience"
