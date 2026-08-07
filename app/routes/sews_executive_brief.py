from fastapi import APIRouter, Depends
from supabase import Client

from app.routes.sews_evidence import (
    get_sews_supabase_client,
)
from app.services.sews_executive_brief_service import (
    SEWSExecutiveBriefService,
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
