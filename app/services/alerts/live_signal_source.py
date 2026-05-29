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


def fetch_live_signals(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Pull real signals from Supabase instead of mock RAW_ALERTS.
    Tries strategic_alerts first, then risk_signals.
    """
    supabase = get_supabase_client()

    if not supabase:
        return []

    tables_to_try = ["strategic_alerts", "risk_signals"]

    for table in tables_to_try:
        try:
            res = (
                supabase.table(table)
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

            rows = res.data or []

            if rows:
                return [normalize_signal(row) for row in rows]

        except Exception as e:
            print(f"[alerts] Could not fetch from {table}: {e}")

    return []


def normalize_signal(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": row.get("id") or row.get("alert_id"),
        "title": row.get("title") or row.get("headline") or "Untitled Signal",
        "summary": row.get("summary") or row.get("description") or row.get("content") or "",
        "source": row.get("source") or row.get("provider") or "Live Signal Feed",
        "url": row.get("url") or row.get("source_url") or "",
        "score": row.get("score") or row.get("risk_score") or row.get("severity_score") or 50,
        "created_at": row.get("created_at") or row.get("published_at"),
        "domains": row.get("domains") or row.get("domain"),
    }
