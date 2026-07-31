from fastapi import APIRouter, HTTPException

from app.schemas.sews import AssessmentRequest, AssessmentResult
from app.services.sews_engine import assess

router = APIRouter(prefix="/api/sews", tags=["Strategic Early Warning"])


@router.get("/health")
async def sews_health() -> dict:
    return {
        "status": "success",
        "service": "sews",
        "engine": "deterministic",
        "formula_version": "sews-logit-v1",
    }


@router.post("/assess", response_model=AssessmentResult)
async def run_assessment(
    payload: AssessmentRequest,
) -> AssessmentResult:
    try:
        return assess(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
