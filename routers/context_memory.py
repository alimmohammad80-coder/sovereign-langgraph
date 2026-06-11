from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import os

load_dotenv(dotenv_path=Path(".env"))

router = APIRouter(prefix="/api/context-memory", tags=["Context Memory"])

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None


class ContextMemorySave(BaseModel):
    source_module: str
    target_module: Optional[str] = None
    country_name: Optional[str] = None
    iso3: Optional[str] = None
    report_id: Optional[str] = None
    selected_question: Optional[str] = None
    context_payload: Dict[str, Any]


def require_supabase():
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")


@router.get("/health")
def health():
    return {
        "status": "ok",
        "module": "context_memory",
        "supabase_configured": bool(supabase),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/save")
def save_context(payload: ContextMemorySave):
    require_supabase()

    row = payload.model_dump()
    res = supabase.table("report_context_memory").insert(row).execute()

    return {
        "status": "success",
        "data": res.data[0] if res.data else row
    }


@router.get("/latest")
def latest_context(
    country: Optional[str] = None,
    iso3: Optional[str] = None,
    source_module: Optional[str] = None,
    target_module: Optional[str] = None
):
    require_supabase()

    q = supabase.table("report_context_memory").select("*")

    if country:
        q = q.eq("country_name", country)

    if iso3:
        q = q.eq("iso3", iso3.upper())

    if source_module:
        q = q.eq("source_module", source_module)

    if target_module:
        q = q.eq("target_module", target_module)

    res = q.order("created_at", desc=True).limit(1).execute()

    return {
        "status": "success",
        "data": res.data[0] if res.data else None
    }
