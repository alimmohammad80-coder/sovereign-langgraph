from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.routes.sews_evidence import (
    get_sews_supabase_client,
)
from app.services.sews_executive_brief_service import (
    SEWSExecutiveBriefService,
)
from app.services.sews_evidence_context_service import (
    SEWSEvidenceContextService,
)


router = APIRouter(
    prefix="/api/sews",
    tags=["SEWS Executive Brief"],
)


def get_db() -> Client:
    return get_sews_supabase_client()


@router.get("/executive-brief")
def executive_brief(
    db: Client = Depends(get_db),
):
    return SEWSExecutiveBriefService(
        db
    ).build()


@router.get("/warning-problems/{problem_key}/evidence-context")
def warning_evidence_context(
    problem_key: str,
    limit: int = Query(default=100, ge=1, le=250),
    db: Client = Depends(get_db),
):
    """Return source-accurate evidence linked to a warning problem.

    This endpoint follows the canonical observation/evidence relationship in
    the database. It intentionally does not infer provenance by matching
    article titles.
    """
    context = SEWSEvidenceContextService(db).build(problem_key, limit=limit)
    documents = context.get("documents") or []
    return {
        "status": "success",
        "problem_key": problem_key,
        "count": len(documents),
        "data": documents,
        "quality": context.get("quality") or {},
    }
