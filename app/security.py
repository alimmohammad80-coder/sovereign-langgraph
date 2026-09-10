"""Central authentication and module authorization for the canonical API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from services.control_plane_auth import build_user_context, verify_supabase_token


# Non-sensitive bootstrap/health routes that must load before a user can make an
# intelligence decision. Intelligence reports, scores, forecasts and live runs
# remain protected below.
PUBLIC_PATHS = frozenset({
    "/",
    "/health",
    "/api/platform/health",
    "/api/country-intelligence/countries",
})


@dataclass(frozen=True)
class RouteEntitlement:
    prefixes: tuple[str, ...]
    module: str


# Ordered most-specific first. Every intelligence API family must appear here;
# an unclassified /api route is denied rather than silently becoming available.
ROUTE_ENTITLEMENTS = (
    RouteEntitlement(("/api/financial-corporate", "/api/financial", "/api/corporate"), "financial_risk"),
    RouteEntitlement(("/api/country",), "country_intelligence"),
    RouteEntitlement(("/api/conflict",), "conflict_forecasting"),
    RouteEntitlement(("/api/supply-chain",), "supply_chain"),
    RouteEntitlement(("/api/cyber",), "cyber"),
    RouteEntitlement(("/api/sews", "/api/early-warning", "/api/warnings"), "early_warning"),
    RouteEntitlement(("/api/scenario", "/api/simulation", "/api/siam"), "scenario_simulation"),
    RouteEntitlement(("/api/knowledge", "/api/context-memory"), "knowledge_graph"),
    RouteEntitlement(("/api/alert",), "alerts"),
    RouteEntitlement(("/api/strategic", "/api/agent"), "strategic_agent"),
    RouteEntitlement(("/api/reports",), "strategic_agent"),
    RouteEntitlement(("/api/intel",), "knowledge_graph"),
    RouteEntitlement(("/api/global", "/api/intelligence", "/api/fusion", "/api/risk", "/api/signals", "/api/dashboard", "/api/news", "/api/gdelt"), "country_intelligence"),
    RouteEntitlement(("/api/ingest", "/api/ingestion"), "country_intelligence"),
    RouteEntitlement(("/dashboard", "/signals", "/ingest"), "country_intelligence"),
)

# Authenticated account/control-plane APIs do not expose intelligence output.
AUTHENTICATED_ONLY_PREFIXES = ("/api/module-access", "/api/usage")


def required_module(path: str) -> str | None:
    if path.startswith(AUTHENTICATED_ONLY_PREFIXES):
        return None
    for rule in ROUTE_ENTITLEMENTS:
        if path.startswith(rule.prefixes):
            return rule.module
    return "__default_deny__" if path.startswith("/api/") else None


def _bearer_token(value: str | None) -> str | None:
    if not value:
        return None
    parts = value.split()
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
        return None
    return parts[1]


def _has_access(context: dict, module: str) -> bool:
    access = context.get("access") or {}
    if access.get("is_admin") or access.get("is_internal"):
        return True
    return module in set(access.get("modules") or [])


class PlatformSecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        if request.method == "OPTIONS" or request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        token = _bearer_token(request.headers.get("authorization"))
        if token is None:
            return JSONResponse({"detail": "Missing or malformed bearer token"}, status_code=401)

        try:
            token_user = verify_supabase_token(token)
            user_id = token_user.get("id") or token_user.get("sub")
            if not user_id:
                raise ValueError("token has no user identity")
        except Exception:
            # Authentication must not leak provider/network/configuration errors.
            return JSONResponse({"detail": "Invalid bearer token"}, status_code=401)

        try:
            # Authorization/account context must be read from the same application
            # control plane that issued the session, under the caller's RLS identity.
            context = build_user_context(str(user_id), token)
        except Exception:
            # A verified identity without a usable account context has no access.
            return JSONResponse({"detail": "Account context unavailable"}, status_code=403)

        module = required_module(request.url.path)
        if module and not _has_access(context, module):
            return JSONResponse({"detail": "Module entitlement required"}, status_code=403)

        context_user = context.get("user") or {}
        # Downstream code must use these token-derived values, never request input.
        request.state.auth_user = token_user
        request.state.account_context = context
        request.state.user_id = str(user_id)
        request.state.tenant_id = (
            token_user.get("tenant_id")
            or (token_user.get("app_metadata") or {}).get("tenant_id")
            or context_user.get("tenant_id")
        )
        return await call_next(request)


def entitlement_modules() -> Iterable[str]:
    return {rule.module for rule in ROUTE_ENTITLEMENTS}
