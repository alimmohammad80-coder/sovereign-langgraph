from fastapi import APIRouter, Header, HTTPException

from services.agent_context_service import build_user_context, verify_supabase_token


router = APIRouter()


def _extract_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization Bearer token")
    return authorization.split(" ", 1)[1].strip()


@router.get("/module-access")
def get_module_access(authorization: str | None = Header(default=None)):
    token = _extract_token(authorization)
    user = verify_supabase_token(token)
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid authenticated user")

    context = build_user_context(user_id)
    return {
        "status": context.get("status"),
        "reason": context.get("reason"),
        "user": context.get("user"),
        "access": context.get("access", {}),
    }
