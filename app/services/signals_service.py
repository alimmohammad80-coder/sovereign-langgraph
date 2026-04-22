from app.services.supabase_service import supabase

def get_recent_normalized_signals(limit=50):
    result = (
        supabase.table("normalized_signals")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data if result.data else []

def curate_signals(limit=50):
    rows = get_recent_normalized_signals(limit=limit)

    curated = []
    for row in rows:
        title = row.get("title") or ""
        summary = row.get("summary") or ""

        # simple English-only filter:
        # keep rows that are mostly ASCII in title+summary
        combined = f"{title} {summary}".strip()
        if not combined:
            continue

        ascii_ratio = sum(1 for ch in combined if ord(ch) < 128) / max(len(combined), 1)
        if ascii_ratio < 0.85:
            continue

        curated.append({
            "id": row.get("id"),
            "title": title,
            "summary": summary if summary else "Recent development identified and prioritized for analysis.",
            "country": row.get("country"),
            "region": row.get("region"),
            "category": row.get("topic"),
            "confidence": row.get("confidence_score"),
            "updated_at": row.get("created_at")
        })

    return curated
