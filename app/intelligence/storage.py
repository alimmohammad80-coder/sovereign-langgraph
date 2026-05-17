import os
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def store_intelligence_run(result: dict):
    payload = {
        "module": result.get("module"),
        "entity": result.get("entity"),
        "indicator": result.get("indicator"),
        "score": result.get("score"),
        "level": result.get("level"),
        "executive_judgment": result.get("executive_judgment"),
        "strategic_assessment": result.get("strategic_assessment"),
        "full_result": result,
    }

    return supabase.table("intelligence_runs").insert(payload).execute()
