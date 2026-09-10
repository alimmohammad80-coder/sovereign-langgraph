from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from routes.financial_command import financial_command_snapshot
from services.financial_corporate.persistence import FinancialHistoryStore


router = APIRouter(prefix="/api/financial/history", tags=["Financial Risk Command History"])
store = FinancialHistoryStore()


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
    return {
        "status": result.get("status", "unknown"),
        "symbol": normalized_symbol,
        "count": len(result.get("items") or []),
        "data": result.get("items") or [],
        "error": result.get("error"),
    }
