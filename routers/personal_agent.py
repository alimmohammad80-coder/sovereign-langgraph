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
