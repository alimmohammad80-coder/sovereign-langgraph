import os
import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests
from fastapi import HTTPException


SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

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


def _headers(service_role: bool = True) -> Dict[str, str]:
    key = SUPABASE_SERVICE_ROLE_KEY if service_role else SUPABASE_ANON_KEY
    if not SUPABASE_URL or not key:
        raise HTTPException(status_code=500, detail="Supabase environment variables are missing")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def verify_supabase_token(access_token: str) -> Dict[str, Any]:
    if not access_token:
        raise HTTPException(status_code=401, detail="Missing access token")

    key = SUPABASE_ANON_KEY or SUPABASE_SERVICE_ROLE_KEY
    res = requests.get(
        f"{SUPABASE_URL}/auth/v1/user",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {access_token}",
        },
        timeout=15,
    )

    if res.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Supabase access token")

    return res.json()


def table_select(table: str, query: str = "") -> List[Dict[str, Any]]:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if query:
        url += f"?{query}"

    try:
        res = requests.get(url, headers=_headers(True), timeout=20)
    except Exception:
        return []

    if res.status_code in (200, 206):
        data = res.json()
        return data if isinstance(data, list) else []

    # Optional tables should not crash the whole context packet.
    return []


def table_insert(table: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    res = requests.post(
        url,
        headers={**_headers(True), "Prefer": "return=representation"},
        json=payload,
        timeout=20,
    )

    if res.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=f"Failed to insert into {table}: {res.text}")

    data = res.json()
    if isinstance(data, list) and data:
        return data[0]
    return {}


def first(rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return rows[0] if rows else None


def get_enabled_modules(user_id: str, profile: Dict[str, Any]) -> List[str]:
    role = profile.get("role")
    plan = profile.get("plan")
    subscription_status = profile.get("subscription_status")

    if role == "admin" or plan == "internal" or subscription_status == "internal":
        return ALL_MODULES

    rows = table_select(
        "module_access",
        f"select=module_key,enabled&user_id=eq.{quote(user_id)}&enabled=eq.true",
    )
    modules = [r.get("module_key") for r in rows if r.get("module_key")]

    if modules:
        return modules

    # Fallback if Stripe payment updated plan but module_access rows are missing.
    if subscription_status == "active":
        return PLAN_MODULES.get(plan, [])

    return []


def build_recommendations(context: Dict[str, Any]) -> Dict[str, Any]:
    modules = set(context.get("access", {}).get("modules", []))
    interests = context.get("interests", {}) or {}
    portfolios = context.get("portfolios", []) or []

    countries = interests.get("countries_of_interest") or []
    sectors = interests.get("sectors_of_interest") or []
    preferred_modules = interests.get("preferred_modules") or []

    actions = []
    upgrades = []

    top_country = countries[0] if countries else None
    supply_chain_sectors = {
        "Semiconductors",
        "Energy",
        "Shipping",
        "Ports",
        "LNG",
        "Oil & Gas",
        "Critical Minerals",
        "Supply Chain Chokepoints",
    }

    if "country_intelligence" in modules and top_country:
        actions.append({
            "title": f"Run Country Intelligence on {top_country}",
            "module_key": "country_intelligence",
            "route": "/country-intelligence",
        })

    if "early_warning" in modules:
        actions.append({
            "title": "Run 30-day Strategic Early Warning",
            "module_key": "early_warning",
            "route": "/early-warning",
        })

    if "alerts" in modules:
        actions.append({
            "title": "Review latest alerts related to your watchlist",
            "module_key": "alerts",
            "route": "/alerts",
        })

    if any(s in supply_chain_sectors for s in sectors):
        if "supply_chain" in modules:
            actions.append({
                "title": "Check Supply Chain Risk",
                "module_key": "supply_chain",
                "route": "/supply-chain",
            })
        else:
            upgrades.append({
                "title": "Supply Chain Risk requires Professional access",
                "module_key": "supply_chain",
            })

    if "Scenario Simulation Lab" in preferred_modules or "Scenario Simulation" in preferred_modules:
        if "scenario_simulation" in modules:
            actions.append({
                "title": "Run Scenario Simulation",
                "module_key": "scenario_simulation",
                "route": "/scenario-simulation",
            })
        else:
            upgrades.append({
                "title": "Scenario Simulation requires Professional access",
                "module_key": "scenario_simulation",
            })

    if "financial_risk" in modules:
        actions.append({
            "title": "Check Financial Risk",
            "module_key": "financial_risk",
            "route": "/financial-risk",
        })

    if portfolios:
        if "portfolio_intelligence" in modules:
            actions.append({
                "title": "Review Portfolio Exposure",
                "module_key": "portfolio_intelligence",
                "route": "/portfolio-intelligence",
            })
        else:
            upgrades.append({
                "title": "Portfolio Intelligence requires Enterprise access",
                "module_key": "portfolio_intelligence",
            })

    if not context.get("user", {}).get("onboarding_completed"):
        actions.insert(0, {
            "title": "Complete Intelligence Profile",
            "module_key": "onboarding",
            "route": "/onboarding",
        })

    return {
        "actions": actions,
        "upgrade_opportunities": upgrades,
    }


def build_user_context(user_id: str) -> Dict[str, Any]:
    profile = first(table_select("profiles", f"select=*&id=eq.{quote(user_id)}"))

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found for authenticated user")

    plan = profile.get("plan")
    role = profile.get("role")
    subscription_status = profile.get("subscription_status")

    is_admin = role == "admin"
    is_internal = plan == "internal" or subscription_status == "internal"

    allowed_modules = get_enabled_modules(user_id, profile)

    if not is_admin and not is_internal and subscription_status != "active":
        return {
            "status": "access_denied",
            "reason": "active_subscription_required",
            "user": {
                "id": profile.get("id"),
                "email": profile.get("email"),
                "full_name": profile.get("full_name"),
                "role": role,
                "plan": plan,
                "status": profile.get("status"),
                "subscription_status": subscription_status,
                "onboarding_completed": profile.get("onboarding_completed"),
            },
            "access": {
                "modules": [],
                "is_admin": False,
                "is_internal": False,
            },
        }

    intelligence_profile = first(
        table_select("user_intelligence_profiles", f"select=*&user_id=eq.{quote(user_id)}")
    ) or {}

    limits = first(table_select("plan_limits", f"select=*&plan=eq.{quote(plan or '')}")) or {}

    subscriptions = table_select(
        "subscriptions",
        f"select=*&user_id=eq.{quote(user_id)}&order=updated_at.desc&limit=1",
    )

    watchlist = table_select(
        "user_watchlists",
        f"select=*&user_id=eq.{quote(user_id)}&order=created_at.desc",
    )

    portfolios = table_select(
        "user_portfolios",
        f"select=*&user_id=eq.{quote(user_id)}&order=created_at.desc",
    )

    saved_reports = table_select(
        "saved_reports",
        f"select=*&user_id=eq.{quote(user_id)}&order=created_at.desc&limit=10",
    )

    recent_activity = table_select(
        "module_usage_events",
        f"select=*&user_id=eq.{quote(user_id)}&order=created_at.desc&limit=20",
    )

    agent_memory = table_select(
        "personal_agent_memory",
        f"select=*&user_id=eq.{quote(user_id)}&active=eq.true&order=updated_at.desc&limit=20",
    )

    context = {
        "status": "ok",
        "user": {
            "id": profile.get("id"),
            "email": profile.get("email"),
            "full_name": profile.get("full_name"),
            "role": role,
            "plan": plan,
            "status": profile.get("status"),
            "subscription_status": subscription_status,
            "onboarding_completed": profile.get("onboarding_completed"),
        },
        "access": {
            "modules": allowed_modules,
            "is_admin": is_admin,
            "is_internal": is_internal,
        },
        "subscription": first(subscriptions),
        "limits": {
            "monthly_report_limit": limits.get("monthly_report_limit"),
            "watchlist_limit": limits.get("watchlist_limit"),
            "export_limit": limits.get("export_limit"),
            "agent_message_limit": limits.get("agent_message_limit"),
            "usage_this_month": {
                "reports": 0,
                "exports": 0,
                "agent_messages": 0,
            },
        },
        "interests": {
            "priority_interests": intelligence_profile.get("priority_interests") or [],
            "preferred_modules": intelligence_profile.get("preferred_modules") or [],
            "countries_of_interest": intelligence_profile.get("countries_of_interest") or [],
            "regions_of_interest": intelligence_profile.get("regions_of_interest") or [],
            "sectors_of_interest": intelligence_profile.get("sectors_of_interest") or [],
            "indicators_of_interest": intelligence_profile.get("indicators_of_interest") or [],
            "alert_preferences": intelligence_profile.get("alert_preferences") or [],
            "alert_frequency": intelligence_profile.get("alert_frequency"),
        },
        "watchlist": watchlist,
        "portfolios": portfolios,
        "saved_reports": saved_reports,
        "recent_activity": recent_activity,
        "agent_memory": agent_memory,
        "recommendations": [],
    }

    context["recommendations"] = build_recommendations(context)
    return context
