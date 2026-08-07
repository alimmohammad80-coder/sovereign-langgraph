from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.routes.sews_evidence import (
    get_sews_supabase_client,
)
from app.services.sews_operational_intelligence_service import (
    SEWSOperationalIntelligenceService,
)


router = APIRouter(
    prefix="/api/sews",
    tags=["SEWS Operational Intelligence"],
)


def get_db() -> Client:
    return get_sews_supabase_client()


@router.get("/operational-intelligence")
def operational_intelligence(
    propagation_hours: int = Query(
        default=24,
        ge=1,
        le=720,
    ),
    warning_limit: int = Query(
        default=12,
        ge=1,
        le=52,
    ),
    product_limit: int = Query(
        default=8,
        ge=1,
        le=52,
    ),
    db: Client = Depends(get_db),
):
    return SEWSOperationalIntelligenceService(
        db
    ).build(
        propagation_hours=propagation_hours,
        warning_limit=warning_limit,
        product_limit=product_limit,
    )
