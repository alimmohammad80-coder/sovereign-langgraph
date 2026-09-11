from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query

from services.financial_corporate.persistence import FinancialHistoryStore


router = APIRouter(prefix="/history", tags=["Financial Risk Command History"])
store = FinancialHistoryStore()

DIMENSION_KEYS = [
    "financial_resilience",
    "market_stress",
    "supply_chain",
    "geopolitical",
    "sanctions_compliance",
    "governance_operational",
]


def _number(value: Any):
    try:
        return None if value is None else round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _history_point(row: Dict[str, Any]) -> Dict[str, Any]:
    snapshot = row.get("snapshot_json") if isinstance(row.get("snapshot_json"), dict) else {}
    dimensions = snapshot.get("dimensions") if isinstance(snapshot.get("dimensions"), list) else []
    by_key = {
        item.get("key"): _number(item.get("score"))
        for item in dimensions
        if isinstance(item, dict) and item.get("key")
    }
    return {
        "id": row.get("id"),
        "captured_at": row.get("captured_at"),
        "risk_score": _number(row.get("risk_score")),
        "risk_level": row.get("risk_level"),
        "confidence_score": _number(row.get("confidence_score")),
        "methodology": row.get("methodology"),
        "dimensions": {key: by_key.get(key) for key in DIMENSION_KEYS},
        "largest_pressure": ((snapshot.get("explanation") or {}).get("largest_pressure") or {}).get("label"),
        "strongest_offset": ((snapshot.get("explanation") or {}).get("strongest_offset") or {}).get("label"),
    }


@router.get("/status")
def financial_history_status():
    return {
        "status": "ok" if store.configured else "disabled",
        "configured": store.configured,
        "snapshot_table": store.snapshot_table,
        "report_table": store.report_table,
        "mode": "supabase_postgrest_fail_open",
    }


@router.post("/capture/{symbol}")
def capture_financial_snapshot(symbol: str):
    normalized_symbol = symbol.strip().upper()
    if not normalized_symbol:
        raise HTTPException(status_code=400, detail="Ticker symbol is required")
    # Lazy import avoids a module cycle when this router is mounted by financial_command.
    from routes.financial_command import financial_command_snapshot

    response = financial_command_snapshot(normalized_symbol)
    snapshot = response.get("data") or {}
    persisted = store.save_snapshot(normalized_symbol, snapshot)
    return {
        "status": "success" if persisted.get("persisted") else persisted.get("status", "partial"),
        "symbol": normalized_symbol,
        "persistence": persisted,
        "data": snapshot,
    }


@router.get("/{symbol}")
def list_financial_history(symbol: str, limit: int = Query(30, ge=1, le=200)):
    normalized_symbol = symbol.strip().upper()
    if not normalized_symbol:
        raise HTTPException(status_code=400, detail="Ticker symbol is required")
    result = store.list_snapshots(normalized_symbol, limit=limit)
    points: List[Dict[str, Any]] = [_history_point(row) for row in (result.get("items") or [])]
    points.reverse()
    previous = None
    for point in points:
        score = point.get("risk_score")
        point["change_from_previous"] = None if score is None or previous is None else round(score - previous, 2)
        if score is not None:
            previous = score
    return {
        "status": result.get("status", "unknown"),
        "symbol": normalized_symbol,
        "count": len(points),
        "data": points,
        "error": result.get("error"),
    }
