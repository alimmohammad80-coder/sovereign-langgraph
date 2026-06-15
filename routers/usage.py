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
