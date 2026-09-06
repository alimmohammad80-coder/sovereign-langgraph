from __future__ import annotations

from threading import RLock
from typing import Dict, List, Literal, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field

from routes.financial_corporate_integrated import live_integrated_snapshot
from services.financial_corporate.report_generator import (
    FinancialCorporateReportGenerator,
    ReportOptions,
)


router = APIRouter(
    prefix="/api/financial-corporate/reports",
    tags=["Financial & Corporate Intelligence Reports"],
)

report_generator = FinancialCorporateReportGenerator()
_REPORT_STORE: Dict[str, Dict] = {}
_REPORT_LOCK = RLock()


class FinancialCorporateReportRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=16)
    report_type: Literal["executive_intelligence", "due_diligence"] = "executive_intelligence"
    depth: Literal["brief", "comprehensive", "deep"] = "comprehensive"
    forecast_horizons: List[Literal["30d", "90d", "180d"]] = Field(
        default_factory=lambda: ["30d", "90d", "180d"]
    )
    citation_style: Literal["chicago"] = "chicago"
    include_methodology: bool = True


@router.get("/status")
def report_status():
    return {
        "status": "ok",
        "module": "Financial & Corporate Risk Intelligence Reports",
        "generator": "financial_corporate_evidence_grounded_report_v1",
        "score_authority": "integrated_snapshot",
        "ai_generated_score": False,
        "citation_style": "chicago_notes",
        "claim_validation": True,
        "exports": ["json", "markdown", "html"],
        "rules": [
            "Report generation cannot create or modify risk scores.",
            "Facts, judgments, and forecasts require evidence references.",
            "Forecasts are directional unless an upstream model explicitly supplies calibrated probabilities.",
            "Negative screening is not converted into zero risk.",
            "Downstream diversion is not represented as company misconduct.",
            "Cyber product and ecosystem evidence is not represented as a direct enterprise incident without victim attribution.",
        ],
    }


@router.post("/generate")
def generate_report(payload: FinancialCorporateReportRequest):
    symbol = payload.symbol.strip().upper()
    if not symbol:
        raise HTTPException(status_code=400, detail="Ticker symbol is required")

    live = live_integrated_snapshot(symbol)
    snapshot = live.get("data") if isinstance(live, dict) else None
    if not isinstance(snapshot, dict):
        raise HTTPException(status_code=502, detail="Integrated snapshot was not available")

    try:
        report = report_generator.generate(
            snapshot,
            ReportOptions(
                report_type=payload.report_type,
                depth=payload.depth,
                forecast_horizons=tuple(payload.forecast_horizons),
                citation_style=payload.citation_style,
                include_methodology=payload.include_methodology,
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    report_id = str(uuid4())
    report["report_id"] = report_id
    report["symbol"] = symbol
    report["source_collection_status"] = live.get("status", "unknown")
    report["source_collection_errors"] = live.get("collection_errors") or []

    with _REPORT_LOCK:
        _REPORT_STORE[report_id] = report

    return {
        "status": "success",
        "report_id": report_id,
        "symbol": symbol,
        "data": report,
    }


@router.get("/{report_id}")
def get_report(report_id: str):
    with _REPORT_LOCK:
        report = _REPORT_STORE.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found in this application instance")
    return {"status": "success", "report_id": report_id, "data": report}


@router.get("/{report_id}/status")
def get_report_generation_status(report_id: str):
    with _REPORT_LOCK:
        report = _REPORT_STORE.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found in this application instance")
    return {
        "status": "complete",
        "report_id": report_id,
        "symbol": report.get("symbol"),
        "generated_at": report.get("generated_at"),
        "claim_validation": report.get("claim_validation"),
    }


@router.get("/{report_id}/export")
def export_report(
    report_id: str,
    format: Literal["markdown", "html"] = Query("markdown"),
):
    with _REPORT_LOCK:
        report = _REPORT_STORE.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found in this application instance")

    if format == "html":
        return HTMLResponse(report_generator.render_html(report))
    return PlainTextResponse(
        report_generator.render_markdown(report),
        media_type="text/markdown; charset=utf-8",
    )
