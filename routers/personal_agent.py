from fastapi import APIRouter, Header, HTTPException

from services.agent_context_service import build_user_context, verify_supabase_token


router = APIRouter()


def _extract_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization Bearer token")
    return authorization.split(" ", 1)[1].strip()


@router.get("/context")
def get_agent_context(authorization: str | None = Header(default=None)):
    token = _extract_token(authorization)
    user = verify_supabase_token(token)
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid authenticated user")
    return build_user_context(user_id)


@router.post("/recommendations")
def get_agent_recommendations(authorization: str | None = Header(default=None)):
    token = _extract_token(authorization)
    user = verify_supabase_token(token)
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid authenticated user")
    context = build_user_context(user_id)
    return {
        "status": context.get("status"),
        "recommendations": context.get("recommendations", {}),
        "access": context.get("access", {}),
        "interests": context.get("interests", {}),
    }


@router.get("/context/admin-test")
def get_agent_context_admin_test(
    email: str,
    x_admin_test_key: str | None = Header(default=None, alias="X-Admin-Test-Key")
):
    import os
    from fastapi import HTTPException
    from services.agent_context_service import table_select, build_user_context
    from urllib.parse import quote

    expected_key = os.getenv("ADMIN_TEST_KEY")

    if not expected_key:
        raise HTTPException(status_code=500, detail="ADMIN_TEST_KEY is not configured")

    if not x_admin_test_key or x_admin_test_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid admin test key")

    rows = table_select(
        "profiles",
        f"select=*&email=eq.{quote(email)}&limit=1"
    )

    if not rows:
        raise HTTPException(status_code=404, detail=f"No profile found for email: {email}")

    user_id = rows[0].get("id")

    if not user_id:
        raise HTTPException(status_code=404, detail="Profile found but user id is missing")

    return build_user_context(user_id)


@router.get("/memory/admin-test")
def get_agent_memory_admin_test(
    email: str,
    x_admin_test_key: str | None = Header(default=None, alias="X-Admin-Test-Key")
):
    import os
    from fastapi import HTTPException
    from services.agent_context_service import table_select
    from urllib.parse import quote

    expected_key = os.getenv("ADMIN_TEST_KEY")

    if not expected_key:
        raise HTTPException(status_code=500, detail="ADMIN_TEST_KEY is not configured")

    if not x_admin_test_key or x_admin_test_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid admin test key")

    rows = table_select("profiles", f"select=*&email=eq.{quote(email)}&limit=1")

    if not rows:
        raise HTTPException(status_code=404, detail=f"No profile found for email: {email}")

    user_id = rows[0].get("id")

    memory = table_select(
        "personal_agent_memory",
        f"select=*&user_id=eq.{quote(user_id)}&active=eq.true&order=updated_at.desc"
    )

    return {
        "status": "ok",
        "user_id": user_id,
        "email": email,
        "memory": memory
    }


from pydantic import BaseModel
from typing import Any, Dict


class AdminMemoryPayload(BaseModel):
    memory_type: str
    memory_key: str
    memory_value: Dict[str, Any]
    confidence: float = 1.0
    source: str = "admin_test"


@router.post("/memory/admin-test")
def create_agent_memory_admin_test(
    payload: AdminMemoryPayload,
    email: str,
    x_admin_test_key: str | None = Header(default=None, alias="X-Admin-Test-Key")
):
    import os
    import requests
    from fastapi import HTTPException
    from services.agent_context_service import SUPABASE_URL, _headers, table_select
    from urllib.parse import quote

    expected_key = os.getenv("ADMIN_TEST_KEY")

    if not expected_key:
        raise HTTPException(status_code=500, detail="ADMIN_TEST_KEY is not configured")

    if not x_admin_test_key or x_admin_test_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid admin test key")

    rows = table_select("profiles", f"select=*&email=eq.{quote(email)}&limit=1")

    if not rows:
        raise HTTPException(status_code=404, detail=f"No profile found for email: {email}")

    user_id = rows[0].get("id")

    body = {
        "user_id": user_id,
        "memory_type": payload.memory_type,
        "memory_key": payload.memory_key,
        "memory_value": payload.memory_value,
        "confidence": payload.confidence,
        "source": payload.source,
        "active": True
    }

    res = requests.post(
        f"{SUPABASE_URL}/rest/v1/personal_agent_memory",
        headers={**_headers(True), "Prefer": "resolution=merge-duplicates,return=representation"},
        json=body,
        timeout=20
    )

    if res.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=f"Failed to save memory: {res.text}")

    return {
        "status": "ok",
        "memory": res.json()
    }


class AdminSavedReportPayload(BaseModel):
    module_key: str
    title: str
    report_data: Dict[str, Any]
    country: str | None = None
    region: str | None = None
    sector: str | None = None
    timeframe: str | None = None
    summary: str | None = None


@router.post("/saved-report/admin-test")
def create_saved_report_admin_test(
    payload: AdminSavedReportPayload,
    email: str,
    x_admin_test_key: str | None = Header(default=None, alias="X-Admin-Test-Key")
):
    import os
    import requests
    from fastapi import HTTPException
    from services.agent_context_service import SUPABASE_URL, _headers, table_select
    from urllib.parse import quote

    expected_key = os.getenv("ADMIN_TEST_KEY")

    if not expected_key:
        raise HTTPException(status_code=500, detail="ADMIN_TEST_KEY is not configured")

    if not x_admin_test_key or x_admin_test_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid admin test key")

    rows = table_select("profiles", f"select=*&email=eq.{quote(email)}&limit=1")

    if not rows:
        raise HTTPException(status_code=404, detail=f"No profile found for email: {email}")

    user_id = rows[0].get("id")

    body = {
        "user_id": user_id,
        "module_key": payload.module_key,
        "title": payload.title,
        "country": payload.country,
        "region": payload.region,
        "sector": payload.sector,
        "timeframe": payload.timeframe,
        "report_data": payload.report_data,
        "summary": payload.summary,
    }

    res = requests.post(
        f"{SUPABASE_URL}/rest/v1/saved_reports",
        headers={**_headers(True), "Prefer": "return=representation"},
        json=body,
        timeout=20
    )

    if res.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=f"Failed to save report: {res.text}")

    return {
        "status": "ok",
        "saved_report": res.json()
    }


@router.get("/saved-reports/admin-test")
def get_saved_reports_admin_test(
    email: str,
    x_admin_test_key: str | None = Header(default=None, alias="X-Admin-Test-Key")
):
    import os
    from fastapi import HTTPException
    from services.agent_context_service import table_select
    from urllib.parse import quote

    expected_key = os.getenv("ADMIN_TEST_KEY")

    if not expected_key:
        raise HTTPException(status_code=500, detail="ADMIN_TEST_KEY is not configured")

    if not x_admin_test_key or x_admin_test_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid admin test key")

    rows = table_select("profiles", f"select=*&email=eq.{quote(email)}&limit=1")

    if not rows:
        raise HTTPException(status_code=404, detail=f"No profile found for email: {email}")

    user_id = rows[0].get("id")

    reports = table_select(
        "saved_reports",
        f"select=*&user_id=eq.{quote(user_id)}&order=created_at.desc"
    )

    return {
        "status": "ok",
        "user_id": user_id,
        "email": email,
        "saved_reports": reports
    }


class AdminBriefingPayload(BaseModel):
    prompt: str | None = None
    briefing_type: str = "executive"
    timeframe: str = "30 days"


@router.post("/briefing/admin-test")
def create_agent_briefing_admin_test(
    payload: AdminBriefingPayload,
    email: str,
    x_admin_test_key: str | None = Header(default=None, alias="X-Admin-Test-Key")
):
    import os
    import requests
    from fastapi import HTTPException
    from services.agent_context_service import table_select, build_user_context
    from urllib.parse import quote

    expected_key = os.getenv("ADMIN_TEST_KEY")

    if not expected_key:
        raise HTTPException(status_code=500, detail="ADMIN_TEST_KEY is not configured")

    if not x_admin_test_key or x_admin_test_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid admin test key")

    rows = table_select("profiles", f"select=*&email=eq.{quote(email)}&limit=1")

    if not rows:
        raise HTTPException(status_code=404, detail=f"No profile found for email: {email}")

    user_id = rows[0].get("id")
    context = build_user_context(user_id)

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured")

    user = context.get("user", {})
    interests = context.get("interests", {})
    memory = context.get("agent_memory", [])
    saved_reports = context.get("saved_reports", [])
    recent_activity = context.get("recent_activity", [])
    recommendations = context.get("recommendations", {})

    system_prompt = """
You are the Personal Intelligence Agent for Sovereign Intelligence AI.

Your task is to generate a concise, high-quality executive intelligence briefing for the authenticated user.

Use only the provided user context. Do not invent saved reports, activity, countries, sectors, or preferences.

Style:
- Serious intelligence platform tone.
- Concise strategic judgment.
- BLUF first.
- No marketing language.
- No exaggerated claims.
- No unsupported facts.
- If the provided context is limited, say so clearly.

Output format:
1. BLUF
2. Priority Watchlist
3. Current Intelligence Posture
4. Relevant Saved Reports
5. Recent Activity
6. Recommended Next Actions
7. Strategic Guidance

Keep it useful for a founder, analyst, or institutional user.
"""

    user_prompt = {
        "briefing_type": payload.briefing_type,
        "timeframe": payload.timeframe,
        "user_request": payload.prompt,
        "user": user,
        "interests": interests,
        "agent_memory": memory,
        "saved_reports": saved_reports,
        "recent_activity": recent_activity,
        "recommendations": recommendations,
        "access": context.get("access", {}),
    }

    res = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {openai_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": os.getenv("OPENAI_AGENT_MODEL", "gpt-4o-mini"),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": str(user_prompt)},
            ],
            "temperature": 0.2,
            "max_tokens": 1200,
        },
        timeout=60,
    )

    if res.status_code not in (200, 201):
        raise HTTPException(
            status_code=500,
            detail=f"OpenAI briefing generation failed: {res.text}"
        )

    data = res.json()
    briefing = data["choices"][0]["message"]["content"]

    return {
        "status": "ok",
        "briefing_type": payload.briefing_type,
        "timeframe": payload.timeframe,
        "user": user,
        "briefing": briefing,
        "context_used": {
            "interests_count": len(interests.get("countries_of_interest", [])) + len(interests.get("sectors_of_interest", [])),
            "saved_reports_count": len(saved_reports),
            "recent_activity_count": len(recent_activity),
            "memory_count": len(memory),
            "recommendation_count": len(recommendations.get("actions", [])),
        }
    }
