import os
import httpx
from typing import List, Dict, Any

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")


def enabled() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


def headers():
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }


async def save_signals(signals: List[Dict[str, Any]]) -> int:
    if not enabled() or not signals:
        return 0

    rows = []
    for s in signals:
        rows.append({
            "domain": s.get("domain"),
            "title": s.get("title"),
            "summary": s.get("summary"),
            "source": s.get("source"),
            "source_quality": s.get("source_quality"),
            "url": s.get("url"),
            "provider": s.get("provider"),
            "published_at": s.get("published_at"),
            "signal_score": s.get("signal_score"),
            "severity": s.get("severity"),
            "confidence": s.get("confidence"),
            "drivers": s.get("drivers"),
        })

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            f"{SUPABASE_URL}/rest/v1/sovereign_signals",
            headers=headers(),
            json=rows
        )
        r.raise_for_status()

    return len(rows)


async def save_alerts(alerts: List[Dict[str, Any]]) -> int:
    if not enabled() or not alerts:
        return 0

    rows = []
    for a in alerts:
        rows.append({
            "domain": a.get("domain"),
            "title": a.get("title"),
            "executive_judgment": a.get("summary") or a.get("title"),
            "source": a.get("source"),
            "url": a.get("url"),
            "risk_score": a.get("signal_score"),
            "risk_level": a.get("severity"),
            "confidence": a.get("confidence"),
            "drivers": a.get("drivers"),
            "raw_signal": a,
        })

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            f"{SUPABASE_URL}/rest/v1/sovereign_alerts",
            headers=headers(),
            json=rows
        )
        r.raise_for_status()

    return len(rows)


async def fetch_latest_signals(limit: int = 25):
    if not enabled():
        return []

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(
            f"{SUPABASE_URL}/rest/v1/sovereign_signals?select=*&order=created_at.desc&limit={limit}",
            headers=headers()
        )
        r.raise_for_status()
        return r.json()


async def fetch_latest_alerts(limit: int = 25):
    if not enabled():
        return []

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(
            f"{SUPABASE_URL}/rest/v1/sovereign_alerts?select=*&order=created_at.desc&limit={limit}",
            headers=headers()
        )
        r.raise_for_status()
        return r.json()
