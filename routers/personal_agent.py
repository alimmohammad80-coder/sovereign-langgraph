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
