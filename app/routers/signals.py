from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.sovereign_news_ingestion import generate_news_signals

router = APIRouter(prefix="/api/signals", tags=["Sovereign Signals"])


class SignalGenerateRequest(BaseModel):
    query: str = Field(..., description="Search query, e.g. Taiwan Strait PLA semiconductor")
    domains: Optional[List[str]] = Field(default=None, description="chokepoint, supply_chain, conflict, energy, strategic")
    limit: int = 25


@router.post("/generate")
async def generate_signals(payload: SignalGenerateRequest):
    return await generate_news_signals(
        query=payload.query,
        domains=payload.domains,
        limit=payload.limit
    )


@router.get("/health")
async def health():
    return {"status": "ok", "module": "sovereign_signals"}
