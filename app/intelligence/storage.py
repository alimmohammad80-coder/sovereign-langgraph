import os
from supabase import create_client


def get_supabase_client():
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise RuntimeError("Supabase environment variables are missing.")

    return create_client(supabase_url, supabase_key)


def store_intelligence_run(result: dict):
    supabase = get_supabase_client()

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
