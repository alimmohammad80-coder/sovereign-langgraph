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
        saved_report_lines = "\n".join([
            f"- {r.get('title')} ({r.get('module_key')}) — {r.get('summary')}"
            for r in saved_reports[:5]
        ]) or "No saved reports available."

        recent_activity_lines = "\n".join([
            f"- {a.get('module_key')}: {a.get('action')} — {a.get('country') or a.get('sector') or 'general'}"
            for a in recent_activity[:5]
        ]) or "No recent activity available."

        recommendation_lines = "\n".join([
            f"- {a.get('title')}"
            for a in recommendations.get("actions", [])
        ]) or "No recommendations available."

        fallback_briefing = f"""
1. BLUF

The Personal Intelligence Agent generated a fallback briefing because the model provider was unavailable. The backend successfully loaded the user profile, module access, saved reports, recent activity, and memory.

2. Priority Watchlist

Countries of interest:
{", ".join(interests.get("countries_of_interest", [])) or "No countries configured."}

Regions of interest:
{", ".join(interests.get("regions_of_interest", [])) or "No regions configured."}

Sectors of interest:
{", ".join(interests.get("sectors_of_interest", [])) or "No sectors configured."}

3. Current Intelligence Posture

The user is configured as {user.get("role")} with plan {user.get("plan")} and subscription status {user.get("subscription_status")}.

Accessible modules:
{", ".join(context.get("access", {}).get("modules", []))}

4. Relevant Saved Reports

Saved reports available: {len(saved_reports)}.

{saved_report_lines}

5. Recent Activity

Recent activity events available: {len(recent_activity)}.

{recent_activity_lines}

6. Recommended Next Actions

{recommendation_lines}

7. Strategic Guidance

Prioritize the user’s highest-interest countries and sectors, beginning with the saved China Strategic Risk Brief and follow-on Country Intelligence, Early Warning, Supply Chain Risk, and Scenario Simulation workflows.

Model provider error:
{res.text}
"""

        return {
            "status": "fallback",
            "reason": "model_provider_unavailable",
            "briefing_type": payload.briefing_type,
            "timeframe": payload.timeframe,
            "user": user,
            "briefing": fallback_briefing,
            "context_used": {
                "interests_count": len(interests.get("countries_of_interest", [])) + len(interests.get("sectors_of_interest", [])),
                "saved_reports_count": len(saved_reports),
                "recent_activity_count": len(recent_activity),
                "memory_count": len(memory),
                "recommendation_count": len(recommendations.get("actions", [])),
            }
        }

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
