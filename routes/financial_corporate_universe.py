from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from services.financial_corporate import CorporateUniverseService


router = APIRouter(
    prefix="/api/financial-corporate/universe",
    tags=["Financial & Corporate Risk Intelligence"],
)

universe = CorporateUniverseService()


@router.get("/health")
def universe_health():
    return {
        "status": "ok",
        "service": "corporate_universe",
        "local_master": True,
        "sec_edgar": universe.sec.configured,
        "gleif": True,
        "sec_index_cache_ttl_seconds": universe.sec_cache_ttl_seconds,
    }


@router.get("/search")
def search_universe(
    query: str = Query(..., min_length=1),
    country_iso2: Optional[str] = Query(None, min_length=2, max_length=2),
    limit_per_provider: int = Query(15, ge=1, le=50),
):
    return {
        "status": "success",
        "data": universe.search(
            query=query,
            country_iso2=country_iso2,
            limit_per_provider=limit_per_provider,
        ),
    }


@router.get("/sec")
def search_sec_universe(
    query: str = Query(..., min_length=1),
    limit: int = Query(25, ge=1, le=100),
):
    return {
        "status": "success",
        "provider": "sec_edgar",
        "data": universe.search_sec(query, limit=limit),
    }
