from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client

from app.routes.sews_evidence import get_sews_supabase_client
from app.schemas.sews_ai_review import (
    AIReviewRequest,
    AIReviewResponse,
    AssessmentComparisonResponse,
)
from app.services.sews_ai_review_service import (
    SEWSAIReviewError,
    SEWSAIReviewService,
)


router = APIRouter(
    prefix="/api/sews/warning-problems",
    tags=["SEWS AI Strategic Review"],
)


def get_db() -> Client:
    return get_sews_supabase_client()


@router.post(
    "/{problem_key}/ai-review",
    response_model=AIReviewResponse,
)
def create_ai_review(
    problem_key: str,
    payload: AIReviewRequest,
    db: Client = Depends(get_db),
):
    try:
        return SEWSAIReviewService(db).review(
            problem_key,
            payload,
        )
    except SEWSAIReviewError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get(
    "/{problem_key}/assessment-comparison",
    response_model=AssessmentComparisonResponse,
)
def assessment_comparison(
    problem_key: str,
    assessment_id: str = Query(...),
    review_id: str = Query(...),
    db: Client = Depends(get_db),
):
    try:
        return SEWSAIReviewService(db).comparison(
            problem_key,
            assessment_id=assessment_id,
            review_id=review_id,
        )
    except SEWSAIReviewError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
