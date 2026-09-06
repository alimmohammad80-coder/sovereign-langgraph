from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from services.financial_corporate.market_credit import MarketCreditIntelligenceService


router = APIRouter(
    prefix="/api/financial-corporate/market-credit",
    tags=["Financial & Corporate Risk Intelligence - Market & Credit"],
)

service = MarketCreditIntelligenceService()


class CombinedMarketCreditRequest(BaseModel):
    symbol: Optional[str] = None
    market_analysis: Optional[Dict[str, Any]] = None
    credit_analysis: Optional[Dict[str, Any]] = None


@router.get("/status")
def status():
    return {
        "status": "ok",
        "module": "Financial & Corporate Risk Intelligence",
        "layer": "market_credit",
        "providers": service.provider_status(),
        "methodologies": [
            "equity_market_stress_v1",
            "system_credit_conditions_v1",
            "confidence_weighted_market_credit_v1",
        ],
    }


@router.get("/equity/{symbol}")
def equity_market_stress(symbol: str):
    try:
        result = service.company_market_snapshot(symbol)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"status": "success", "data": result}


@router.get("/credit")
def credit_conditions():
    try:
        result = service.credit_snapshot()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"status": "success", "data": result}


@router.get("/combined/{symbol}")
def combined_market_credit(symbol: str):
    result = service.combined_score(symbol=symbol)
    return {"status": "success", "symbol": symbol.upper(), "data": result}


@router.post("/combined")
def combined_from_observations(payload: CombinedMarketCreditRequest):
    result = service.combined_score(
        symbol=payload.symbol,
        market_analysis=payload.market_analysis,
        credit_analysis=payload.credit_analysis,
    )
    return {"status": "success", "data": result}
