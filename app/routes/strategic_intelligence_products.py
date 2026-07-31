from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client

from app.routes.sews_evidence import get_sews_supabase_client
from app.schemas.strategic_intelligence_product import (
    ProductGenerationRequest,
    ProductHistoryResponse,
    StrategicIntelligenceProduct,
)
from app.services.strategic_intelligence_product_service import (
    StrategicIntelligenceProductError,
    StrategicIntelligenceProductService,
)


router = APIRouter(
    prefix="/api/sews/warning-problems",
    tags=["Strategic Intelligence Products"],
)


def get_db() -> Client:
    return get_sews_supabase_client()


@router.post(
    "/{problem_key}/product",
    response_model=StrategicIntelligenceProduct,
)
def generate_product(
    problem_key: str,
    payload: ProductGenerationRequest,
    db: Client = Depends(get_db),
):
    try:
        return StrategicIntelligenceProductService(db).generate(
            problem_key,
            payload,
        )
    except StrategicIntelligenceProductError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get(
    "/{problem_key}/products",
    response_model=ProductHistoryResponse,
)
def product_history(
    problem_key: str,
    db: Client = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, Any]:
    try:
        data = StrategicIntelligenceProductService(db).history(
            problem_key,
            limit=limit,
        )
        return {
            "problem_key": problem_key,
            "count": len(data),
            "data": data,
        }
    except StrategicIntelligenceProductError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
