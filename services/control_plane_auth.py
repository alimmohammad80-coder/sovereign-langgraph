"""Application identity and authorization against the xady Supabase control plane.

This module intentionally contains no analytical Supabase credentials. Browser
sessions are validated against the Lovable-managed identity project and account
state is read under the caller's own RLS identity.
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import requests
from fastapi import HTTPException

AUTH_SUPABASE_URL = os.getenv("AUTH_SUPABASE_URL", "").rstrip("/")
AUTH_SUPABASE_PUBLISHABLE_KEY = os.getenv("AUTH_SUPABASE_PUBLISHABLE_KEY", "")

ALL_MODULES = [
    "country_intelligence",
    "early_warning",
    "alerts",
    "supply_chain",
    "scenario_simulation",
    "conflict_forecasting",
    "financial_risk",
    "portfolio_intelligence",
    "corporate_exposure",
    "knowledge_graph",
    "cyber",
    "strategic_agent",
]

PLAN_MODULES = {
    "starter": ["country_intelligence", "early_warning", "alerts"],
    "professional": [
        "country_intelligence",
        "early_warning",
        "alerts",
        "supply_chain",
        "scenario_simulation",
        "conflict_forecasting",
        "financial_risk",
    ],
    "enterprise": ALL_MODULES,
    "internal": ALL_MODULES,
}

ACTIVE_SUBSCRIPTION_STATUSES = {"active", "trialing", "internal"}

# Auth is on the hot path for every API request. Reuse HTTP connections and
# cache successful identity/account packets briefly to avoid turning every
# dashboard request into several sequential round-trips to Supabase.
_HTTP = requests.Session()
_TOKEN_CACHE_TTL_SECONDS = 45.0
_CONTEXT_CACHE_TTL_SECONDS = 30.0
_TOKEN_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_CONTEXT_CACHE: Dict[Tuple[str, str], Tuple[float, Dict[str, Any]]] = {}
_CACHE_LOCK = Lock()


def _cache_get(cache: dict, key: Any) -> Optional[Dict[str, Any]]:
    now = time.monotonic()
    with _CACHE_LOCK:
        entry = cache.get(key)
        if not entry:
            return None
        expires_at, value = entry
        if expires_at <= now:
            cache.pop(key, None)
            return None
        return value


def _cache_put(cache: dict, key: Any, value: Dict[str, Any], ttl: float) -> None:
    with _CACHE_LOCK:
        cache[key] = (time.monotonic() + ttl, value)
        # Bound memory even if many short-lived tokens arrive at one worker.
        if len(cache) > 512:
            now = time.monotonic()
            expired = [k for k, (expires_at, _) in cache.items() if expires_at <= now]
            for expired_key in expired:
                cache.pop(expired_key, None)
            while len(cache) > 512:
                cache.pop(next(iter(cache)), None)


def _headers(access_token: str) -> Dict[str, str]:
    if not AUTH_SUPABASE_URL or not AUTH_SUPABASE_PUBLISHABLE_KEY:
        raise HTTPException(status_code=500, detail="Auth Supabase environment variables are missing")
    if not access_token:
        raise HTTPException(status_code=401, detail="Missing access token")
    return {
        "apikey": AUTH_SUPABASE_PUBLISHABLE_KEY,
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def verify_supabase_token(access_token: str) -> Dict[str, Any]:
    """Validate the browser session against the Supabase project that issued it."""
    if not access_token:
        raise HTTPException(status_code=401, detail="Missing access token")

    cached = _cache_get(_TOKEN_CACHE, access_token)
    if cached is not None:
        return cached

    try:
        response = _HTTP.get(
            f"{AUTH_SUPABASE_URL}/auth/v1/user",
            headers=_headers(access_token),
            timeout=10,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=503, detail="Auth provider unavailable") from exc

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Supabase access token")
    data = response.json()
    if not isinstance(data, dict):
        raise HTTPException(status_code=401, detail="Invalid Supabase user response")

    _cache_put(_TOKEN_CACHE, access_token, data, _TOKEN_CACHE_TTL_SECONDS)
    return data


def _select(access_token: str, table: str, query: str = "") -> List[Dict[str, Any]]:
    url = f"{AUTH_SUPABASE_URL}/rest/v1/{table}"
    if query:
        url += f"?{query}"
    try:
        response = _HTTP.get(url, headers=_headers(access_token), timeout=10)
    except requests.RequestException as exc:
        raise HTTPException(status_code=503, detail="Account provider unavailable") from exc

    if response.status_code not in (200, 206):
        raise HTTPException(status_code=403, detail=f"Unable to read account table: {table}")
    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="Invalid account provider response") from exc
    return data if isinstance(data, list) else []


def _first(rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return rows[0] if rows else None


def _modules_from_rows(
    profile: Dict[str, Any],
    module_rows: List[Dict[str, Any]],
    is_admin: bool,
) -> List[str]:
    plan = str(profile.get("plan") or "").lower()
    subscription_status = str(profile.get("subscription_status") or "").lower()

    if is_admin or plan == "internal" or subscription_status == "internal":
        return ALL_MODULES

    modules: List[str] = []
    for row in module_rows:
        enabled = row.get("enabled")
        if enabled is False:
            continue
        key = row.get("module_key") or row.get("module") or row.get("module_name")
        if key:
            modules.append(str(key))

    if modules:
        return list(dict.fromkeys(modules))

    if subscription_status in ACTIVE_SUBSCRIPTION_STATUSES:
        return PLAN_MODULES.get(plan, [])
    return []


def build_user_context(user_id: str, access_token: str) -> Dict[str, Any]:
    """Build the minimum trusted account context required by FastAPI.

    xady `profiles.id` is the profile row id. The authenticated Supabase user is
    linked through `profiles.user_id`, so authorization must query `user_id`.
    Successful context is cached briefly because this function is called for
    every protected API request.
    """
    cache_key = (str(user_id), access_token)
    cached = _cache_get(_CONTEXT_CACHE, cache_key)
    if cached is not None:
        return cached

    # These three RLS-scoped reads are independent, so perform them together.
    # This cuts first-request authorization latency from three serial network
    # round-trips to roughly one round-trip.
    with ThreadPoolExecutor(max_workers=3) as pool:
        profile_future = pool.submit(
            _select,
            access_token,
            "profiles",
            f"select=*&user_id=eq.{quote(user_id)}&limit=1",
        )
        roles_future = pool.submit(
            _select,
            access_token,
            "user_roles",
            f"select=role&user_id=eq.{quote(user_id)}",
        )
        modules_future = pool.submit(
            _select,
            access_token,
            "module_access",
            f"select=*&user_id=eq.{quote(user_id)}",
        )
        profile_rows = profile_future.result()
        role_rows = roles_future.result()
        module_rows = modules_future.result()

    profile = _first(profile_rows)
    if not profile:
        raise HTTPException(status_code=403, detail="Profile not found for authenticated user")

    if str(profile.get("user_id")) != str(user_id):
        raise HTTPException(status_code=403, detail="Authenticated user mismatch")

    assigned_roles = {str(row.get("role") or "").lower() for row in role_rows}
    profile_role = str(profile.get("role") or "").lower()
    is_admin = "admin" in assigned_roles or profile_role == "admin"

    plan = str(profile.get("plan") or "").lower()
    subscription_status = str(profile.get("subscription_status") or "").lower()
    is_internal = plan == "internal" or subscription_status == "internal"
    modules = _modules_from_rows(profile, module_rows, is_admin)

    context = {
        "status": "ok" if (is_admin or is_internal or subscription_status in ACTIVE_SUBSCRIPTION_STATUSES) else "access_denied",
        "reason": None if (is_admin or is_internal or subscription_status in ACTIVE_SUBSCRIPTION_STATUSES) else "active_subscription_required",
        "user": {
            "id": str(user_id),
            "profile_id": profile.get("id"),
            "user_id": profile.get("user_id"),
            "email": profile.get("email"),
            "full_name": profile.get("full_name") or profile.get("display_name"),
            "role": profile.get("role"),
            "roles": sorted(r for r in assigned_roles if r),
            "plan": profile.get("plan"),
            "status": profile.get("status"),
            "subscription_status": profile.get("subscription_status"),
            "onboarding_completed": profile.get("onboarding_completed"),
        },
        "access": {
            "modules": modules,
            "is_admin": is_admin,
            "is_internal": is_internal,
        },
    }

    _cache_put(_CONTEXT_CACHE, cache_key, context, _CONTEXT_CACHE_TTL_SECONDS)
    return context
