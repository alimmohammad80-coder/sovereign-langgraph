from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from services.agent_context_service import table_insert, verify_supabase_token


router = APIRouter()


class UsageEvent(BaseModel):
    module_key: str
    action: str
    country: Optional[str] = None
    region: Optional[str] = None
    sector: Optional[str] = None
    indicator: Optional[str] = None
    report_id: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0
    success: bool = True
    error_message: Optional[str] = None


def _extract_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization Bearer token")
    return authorization.split(" ", 1)[1].strip()


@router.post("/track")
def track_usage(event: UsageEvent, authorization: str | None = Header(default=None)):
    token = _extract_token(authorization)
    user = verify_supabase_token(token)
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid authenticated user")

    payload = event.model_dump()
    payload["user_id"] = user_id

    inserted = table_insert("module_usage_events", payload)

    return {
        "status": "ok",
        "event": inserted,
    }


@router.post("/track/admin-test")
def track_usage_admin_test(
    event: UsageEvent,
    email: str,
    x_admin_test_key: str | None = Header(default=None, alias="X-Admin-Test-Key")
):
    import os
    from urllib.parse import quote
    from services.agent_context_service import table_select

    expected_key = os.getenv("ADMIN_TEST_KEY")

    if not expected_key:
        raise HTTPException(status_code=500, detail="ADMIN_TEST_KEY is not configured")

    if not x_admin_test_key or x_admin_test_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid admin test key")

    rows = table_select("profiles", f"select=*&email=eq.{quote(email)}&limit=1")

    if not rows:
        raise HTTPException(status_code=404, detail=f"No profile found for email: {email}")

    user_id = rows[0].get("id")

    payload = event.model_dump()
    payload["user_id"] = user_id

    inserted = table_insert("module_usage_events", payload)

    return {
        "status": "ok",
        "event": inserted
    }
