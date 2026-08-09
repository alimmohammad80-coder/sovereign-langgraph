from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.routes.sews_evidence import get_sews_supabase_client


router = APIRouter(
    prefix="/api/sews",
    tags=["SEWS Warning Baselines"],
)


def get_db() -> Client:
    return get_sews_supabase_client()


@router.get("/warning-problems/{problem_key}/baseline")
def get_warning_baseline(
    problem_key: str,
    db: Client = Depends(get_db),
):
    problems = (
        db.table("sews_warning_problems")
        .select(
            "id,problem_key,title,hypothesis,"
            "horizon_days,state,severity_score"
        )
        .eq("problem_key", problem_key)
        .limit(1)
        .execute()
        .data
        or []
    )

    if not problems:
        raise HTTPException(
            status_code=404,
            detail="Warning problem not found.",
        )

    problem = problems[0]

    baselines = (
        db.table("sews_warning_baselines")
        .select("*")
        .eq("warning_problem_id", problem["id"])
        .limit(1)
        .execute()
        .data
        or []
    )

    if not baselines:
        raise HTTPException(
            status_code=404,
            detail="Baseline intelligence profile not found.",
        )

    return {
        "status": "success",
        "problem": problem,
        "baseline": baselines[0],
    }
