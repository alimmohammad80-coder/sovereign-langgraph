from __future__ import annotations

import os
import secrets
from typing import Any

from fastapi import APIRouter, Header, HTTPException

from app.ingestion.supply_chain import build_supply_chain_orchestrator


router = APIRouter(
    prefix="/api/supply-chain/ingestion",
    tags=["Supply Chain Ingestion"],
)


def _authorize(token: str | None) -> None:
    expected = os.getenv("SUPPLY_CHAIN_INGESTION_TOKEN")
    if expected and (
        not token or not secrets.compare_digest(token, expected)
    ):
        raise HTTPException(
            status_code=403,
            detail="Invalid Supply Chain ingestion token.",
        )


@router.get("/sources")
def supply_chain_ingestion_sources():
    orchestrator = build_supply_chain_orchestrator()
    return {
        "status": "success",
        "sources": orchestrator.available_sources(),
        "configuration": {
            "GDELT": "ready",
            "IMF_PORTWATCH": (
                "ready"
                if os.getenv("PORTWATCH_API_URL")
                else "requires PORTWATCH_API_URL"
            ),
            "GDACS": "ready",
            "USGS": "ready",
            "UN_COMTRADE": "context requires reporter_code",
            "EIA": (
                "context requires eia_route"
                if os.getenv("EIA_API_KEY")
                else "requires EIA_API_KEY and eia_route"
            ),
            "OFAC": "ready",
            "SEC_EDGAR": (
                "context requires company_cik"
                if os.getenv("SEC_USER_AGENT")
                else "requires SEC_USER_AGENT and company_cik"
            ),
            "GLEIF": "context requires company_name",
            "OFFICIAL_FEEDS": "context requires official_feed_urls",
        },
    }


@router.post("/run/{source_key}")
async def run_supply_chain_source(
    source_key: str,
    payload: dict[str, Any] | None = None,
    x_ingestion_token: str | None = Header(default=None),
):
    _authorize(x_ingestion_token)
    orchestrator = build_supply_chain_orchestrator()
    try:
        result = await orchestrator.run_source(
            source_key,
            payload or {},
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    return {
        "status": "success" if result["success"] else "error",
        "result": result,
    }


@router.post("/run")
async def run_supply_chain_sources(
    payload: dict[str, Any] | None = None,
    x_ingestion_token: str | None = Header(default=None),
):
    _authorize(x_ingestion_token)
    payload = payload or {}
    return await build_supply_chain_orchestrator().run_all(
        contexts=payload.get("contexts") or {},
        sources=payload.get("sources"),
    )
