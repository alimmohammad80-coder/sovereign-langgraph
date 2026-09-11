from routes.financial_history import _history_point


def test_history_point_preserves_unknown_dimensions():
    point = _history_point({"risk_score": 41, "snapshot_json": {"dimensions": []}})
    assert point["risk_score"] == 41.0
    assert point["dimensions"]["supply_chain"] is None
    assert point["dimensions"]["geopolitical"] is None
