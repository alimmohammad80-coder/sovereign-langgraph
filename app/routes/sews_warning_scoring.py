from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.routes.sews_evidence import get_sews_supabase_client
from app.schemas.sews_warning_scoring import WarningAssessmentRequest, WarningAssessmentResponse
from app.services.sews_warning_scoring_service import SEWSWarningScoringError, SEWSWarningScoringService

router = APIRouter(prefix="/api/sews/warning-problems", tags=["SEWS Warning Scoring"])


def get_db() -> Client:
    return get_sews_supabase_client()


@router.post("/{problem_key}/assess", response_model=WarningAssessmentResponse)
def assess(problem_key: str, payload: WarningAssessmentRequest, db: Client = Depends(get_db)):
    try:
        return SEWSWarningScoringService(db).assess(problem_key, payload)
    except SEWSWarningScoringError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
