from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.sovereign_news_ingestion import generate_news_signals
from app.services.signal_storage import (
    save_signals,
    save_alerts,
    fetch_latest_signals,
    fetch_latest_alerts,
    enabled as storage_enabled,
)

router = APIRouter(prefix="/api/signals", tags=["Sovereign Signals"])


class SignalGenerateRequest(BaseModel):
    query: str = Field(..., description="Search query")
    domains: Optional[List[str]] = Field(default=None)
    limit: int = 25
    save: bool = True


@router.post("/generate")
async def generate_signals(payload: SignalGenerateRequest):
    result = await generate_news_signals(
        query=payload.query,
        domains=payload.domains,
        limit=payload.limit
    )

    saved_signals = 0
    saved_alerts = 0

    if payload.save:
        saved_signals = await save_signals(result.get("signals", []))
        saved_alerts = await save_alerts(result.get("alerts", []))

    result["storage_enabled"] = storage_enabled()
    result["saved_signals"] = saved_signals
    result["saved_alerts"] = saved_alerts

    return result


@router.get("/latest")
async def latest_signals(limit: int = 25):
    return {
        "status": "success",
        "storage_enabled": storage_enabled(),
        "signals": await fetch_latest_signals(limit)
    }


@router.get("/alerts/latest")
async def latest_alerts(limit: int = 25):
    return {
        "status": "success",
        "storage_enabled": storage_enabled(),
        "alerts": await fetch_latest_alerts(limit)
    }


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "module": "sovereign_signals",
        "storage_enabled": storage_enabled()
    }
