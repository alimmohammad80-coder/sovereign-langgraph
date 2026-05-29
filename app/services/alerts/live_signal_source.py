import os
from typing import List, Dict, Any

try:
    from supabase import create_client
except Exception:
    create_client = None


def get_supabase_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

    if not url or not key or create_client is None:
        return None

    return create_client(url, key)


def normalize_domains(row: Dict[str, Any]):
    domains = row.get("domains")

    if isinstance(domains, list):
        return domains

    if isinstance(domains, str) and domains.strip():
        return [domains]

    domain = row.get("domain")

    if isinstance(domain, str) and domain.strip():
        return [domain]

    return None


def fetch_live_signals(limit: int = 50) -> List[Dict[str, Any]]:
    supabase = get_supabase_client()

    if not supabase:
        print("[alerts] Supabase not configured")
        return []

    try:
        res = (
            supabase.table("live_risk_signals")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        rows = res.data or []
        print(f"[alerts] fetched {len(rows)} rows from live_risk_signals")

        return [normalize_signal(row) for row in rows]

    except Exception as e:
        print(f"[alerts] live_risk_signals fetch failed: {e}")
        return []


def fetch_raw_signals_debug(limit: int = 20):
    supabase = get_supabase_client()

    if not supabase:
        return []

    res = (
        supabase.table("live_risk_signals")
        .select("id,title,source,score,risk_score,domain,domains,created_at,url")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return res.data or []


def normalize_signal(row: Dict[str, Any]) -> Dict[str, Any]:
    score = row.get("risk_score") or row.get("score") or 50

    return {
        "id": row.get("id"),
        "title": row.get("title") or row.get("headline") or "Untitled Signal",
        "summary": row.get("summary") or row.get("description") or row.get("content") or "",
        "source": row.get("source") or row.get("provider") or "Live Signal Feed",
        "url": row.get("url") or row.get("source_url") or "",
        "score": score,
        "risk_score": score,
        "created_at": row.get("created_at") or row.get("published_at"),
        "published_at": row.get("published_at"),
        "domains": normalize_domains(row),
    }
