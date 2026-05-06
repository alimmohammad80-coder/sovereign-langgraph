from dotenv import load_dotenv
load_dotenv()

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
import json
import requests

from supabase import create_client, Client
from openai import OpenAI


# ============================================================
# Sovereign Intelligence — Financial Risk Command
# Backend Route: /api/financial-risk
# ============================================================

router = APIRouter(
    prefix="/api/financial-risk",
    tags=["Financial Risk Command"]
)


# ============================================================
# Environment Variables
# ============================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NEMOTRON_MODEL = os.getenv("NEMOTRON_MODEL", "nvidia/llama-3.1-nemotron-nano-8b-v1")

NEWS_API_KEY = os.getenv("NEWS_API_KEY")


# ============================================================
# Safe Client Initialization
# ============================================================

supabase: Optional[Client] = None
openai_client: Optional[OpenAI] = None
nemotron_client: Optional[OpenAI] = None


if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("[Financial Risk] Supabase configured.")
    except Exception as e:
        print(f"[Financial Risk] Supabase client failed: {e}")
else:
    print("[Financial Risk] Supabase not configured. Check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")


if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        print("[Financial Risk] OpenAI configured.")
    except Exception as e:
        print(f"[Financial Risk] OpenAI client failed: {e}")
else:
    print("[Financial Risk] OpenAI not configured. Check OPENAI_API_KEY.")


if NVIDIA_API_KEY:
    try:
        nemotron_client = OpenAI(
            base_url=NVIDIA_BASE_URL,
            api_key=NVIDIA_API_KEY
        )
        print("[Financial Risk] Nemotron/NVIDIA configured.")
    except Exception as e:
        print(f"[Financial Risk] Nemotron client failed: {e}")
else:
    print("[Financial Risk] Nemotron not configured. Check NVIDIA_API_KEY.")


# ============================================================
# Request Models
# ============================================================

class FinancialRiskRequest(BaseModel):
    country: str = Field(..., min_length=2)
    query: Optional[str] = None


class FinancialScenarioRequest(BaseModel):
    country: str = Field(..., min_length=2)
    shock_type: str = Field(..., min_length=2)
    time_horizon: str = Field(..., min_length=2)
    exposure_type: str = Field(..., min_length=2)


# ============================================================
# Guards and Utilities
# ============================================================

def require_supabase() -> Client:
    if not supabase:
        raise HTTPException(
            status_code=500,
            detail="Supabase is not configured. Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to .env."
        )
    return supabase


def require_openai() -> OpenAI:
    if not openai_client:
        raise HTTPException(
            status_code=500,
            detail="OpenAI is not configured. Add OPENAI_API_KEY to .env."
        )
    return openai_client


def require_nemotron() -> OpenAI:
    if not nemotron_client:
        raise HTTPException(
            status_code=500,
            detail="Nemotron is not configured. Add NVIDIA_API_KEY to .env."
        )
    return nemotron_client


def safe_json_loads(raw: str) -> Dict[str, Any]:
    try:
        return json.loads(raw)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail=f"Model returned invalid JSON: {raw[:500]}"
        )


def risk_level(score: int) -> str:
    if score >= 76:
        return "severe"
    if score >= 56:
        return "high"
    if score >= 31:
        return "moderate"
    return "low"


def normalize_score(value: Any, fallback: int = 50) -> int:
    try:
        score = int(value)
        return max(0, min(100, score))
    except Exception:
        return fallback


# ============================================================
# Health and Status Routes
# ============================================================

@router.get("/health")
def financial_risk_health():
    return {
        "status": "ok",
        "module": "Financial Risk Command",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/api-status")
def financial_risk_api_status():
    return {
        "status": "ok",
        "module": "Financial Risk Command",
        "timestamp": datetime.utcnow().isoformat(),
        "supabase_configured": bool(SUPABASE_URL and SUPABASE_KEY and supabase),
        "openai_configured": bool(OPENAI_API_KEY and openai_client),
        "openai_model": OPENAI_MODEL,
        "nvidia_configured": bool(NVIDIA_API_KEY and nemotron_client),
        "nemotron_model": NEMOTRON_MODEL,
        "nvidia_base_url": NVIDIA_BASE_URL,
        "newsapi_configured": bool(NEWS_API_KEY)
    }


# ============================================================
# External Signal Collection
# ============================================================

def fetch_news_signals(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    if not NEWS_API_KEY:
        return []

    url = "https://newsapi.org/v2/everything"

    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": limit,
        "apiKey": NEWS_API_KEY,
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data.get("articles", [])
    except Exception as e:
        print(f"[Financial Risk] NewsAPI error: {e}")
        return []


@router.get("/live-signals")
def get_live_financial_signals(
    query: str = Query("sovereign debt currency crisis sanctions banking risk"),
    limit: int = Query(10, ge=1, le=50)
):
    articles = fetch_news_signals(query, limit)

    signals = []

    for item in articles:
        if not isinstance(item, dict):
            continue

        signal = {
            "country": None,
            "region": None,
            "signal_type": "financial_risk_news",
            "title": item.get("title"),
            "summary": item.get("description"),
            "severity_score": 50,
            "confidence_score": 60,
            "source_name": item.get("source", {}).get("name") if item.get("source") else None,
            "source_url": item.get("url"),
            "published_at": item.get("publishedAt"),
        }

        signals.append(signal)

        if supabase:
            try:
                supabase.table("financial_risk_signals").insert(signal).execute()
            except Exception as e:
                print(f"[Financial Risk] Supabase signal insert warning: {e}")

    return {
        "status": "success",
        "source": "NewsAPI",
        "query": query,
        "count": len(signals),
        "signals": signals
    }


# ============================================================
# OpenAI Financial Risk Agent
# ============================================================

def generate_openai_financial_brief(
    country: str,
    query: Optional[str],
    news_items: List[Dict[str, Any]]
) -> Dict[str, Any]:

    news_context = "\n".join([
        f"- {item.get('title')} | {item.get('description')} | {item.get('url')}"
        for item in news_items
        if isinstance(item, dict) and item.get("title")
    ])

    prompt = f"""
You are the Sovereign Intelligence Financial Risk Command Agent.

Produce a serious, investor-grade financial risk intelligence assessment.

Country:
{country}

User query:
{query or "General financial risk assessment"}

Recent signal context:
{news_context or "No recent news context available."}

Return ONLY valid JSON with this exact structure:

{{
  "executive_judgment": "",
  "financial_risk_score": 0,
  "risk_level": "",
  "main_drivers": [],
  "key_indicators": [],
  "market_implications": [],
  "corporate_exposure": [],
  "investor_implications": [],
  "early_warning_indicators": [],
  "outlook_30d": "",
  "outlook_90d": "",
  "intelligence_gaps": [],
  "confidence_level": ""
}}

Assessment areas:
- sovereign debt risk
- FX and currency pressure
- inflation and monetary stress
- banking sector fragility
- sanctions and compliance exposure
- commodity-linked financial vulnerability
- capital flight risk
- market volatility
- geopolitical-financial contagion
"""

    response = require_openai().chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a senior financial risk intelligence analyst. Return only valid JSON."
            },
            {
                "role": "user",
                "content": prompt
            },
        ],
        response_format={"type": "json_object"},
    )

    return safe_json_loads(response.choices[0].message.content)


@router.post("/run-agent")
def run_financial_risk_agent(payload: FinancialRiskRequest):
    country = payload.country.strip()
    query = payload.query or f"{country} sovereign debt currency inflation banking sanctions financial risk"

    news_items = fetch_news_signals(query, 10)
    result = generate_openai_financial_brief(country, query, news_items)

    score = normalize_score(result.get("financial_risk_score"), 50)
    level = result.get("risk_level") or risk_level(score)

    briefing = {
        "country": country,
        "query": query,
        "executive_judgment": result.get("executive_judgment"),
        "financial_risk_score": score,
        "risk_level": level,
        "main_drivers": result.get("main_drivers", []),
        "key_indicators": result.get("key_indicators", []),
        "market_implications": result.get("market_implications", []),
        "corporate_exposure": result.get("corporate_exposure", []),
        "investor_implications": result.get("investor_implications", []),
        "early_warning_indicators": result.get("early_warning_indicators", []),
        "outlook_30d": result.get("outlook_30d"),
        "outlook_90d": result.get("outlook_90d"),
        "intelligence_gaps": result.get("intelligence_gaps", []),
        "confidence_level": result.get("confidence_level"),
    }

    if supabase:
        try:
            supabase.table("financial_risk_briefings").insert(briefing).execute()
        except Exception as e:
            briefing["supabase_warning"] = str(e)

    return {
        "engine": "financial_risk_command",
        "status": "success",
        "agent": "openai_financial_risk_agent",
        "model": OPENAI_MODEL,
        "result": briefing
    }


# ============================================================
# Nemotron Financial Risk Agent
# ============================================================

def generate_nemotron_financial_brief(
    country: str,
    query: Optional[str],
    news_items: List[Dict[str, Any]]
) -> Dict[str, Any]:

    news_context = "\n".join([
        f"- {item.get('title')} | {item.get('description')} | {item.get('url')}"
        for item in news_items
        if isinstance(item, dict) and item.get("title")
    ])

    prompt = f"""
You are NVIDIA Nemotron operating as a second-opinion financial risk intelligence model for Sovereign Intelligence.

Assess financial risk for:
{country}

User query:
{query or "General financial risk assessment"}

Recent signal context:
{news_context or "No recent news context available."}

Return ONLY valid JSON with this exact structure:

{{
  "executive_judgment": "",
  "financial_risk_score": 0,
  "risk_level": "",
  "main_drivers": [],
  "key_indicators": [],
  "market_implications": [],
  "corporate_exposure": [],
  "investor_implications": [],
  "early_warning_indicators": [],
  "outlook_30d": "",
  "outlook_90d": "",
  "intelligence_gaps": [],
  "confidence_level": ""
}}

Focus especially on:
- sovereign debt
- FX pressure
- inflation
- reserves
- sanctions
- banking fragility
- commodity-linked exposure
- geopolitical-financial contagion
"""

    response = require_nemotron().chat.completions.create(
        model=NEMOTRON_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a financial risk intelligence model. Return only valid JSON."
            },
            {
                "role": "user",
                "content": prompt
            },
        ],
        temperature=0.2,
        max_tokens=2000,
    )

    return safe_json_loads(response.choices[0].message.content)


@router.post("/run-nemotron-agent")
def run_nemotron_financial_risk_agent(payload: FinancialRiskRequest):
    country = payload.country.strip()
    query = payload.query or f"{country} sovereign debt currency inflation banking sanctions financial risk"

    news_items = fetch_news_signals(query, 10)
    result = generate_nemotron_financial_brief(country, query, news_items)

    score = normalize_score(result.get("financial_risk_score"), 50)
    level = result.get("risk_level") or risk_level(score)

    briefing = {
        "country": country,
        "query": query,
        "executive_judgment": result.get("executive_judgment"),
        "financial_risk_score": score,
        "risk_level": level,
        "main_drivers": result.get("main_drivers", []),
        "key_indicators": result.get("key_indicators", []),
        "market_implications": result.get("market_implications", []),
        "corporate_exposure": result.get("corporate_exposure", []),
        "investor_implications": result.get("investor_implications", []),
        "early_warning_indicators": result.get("early_warning_indicators", []),
        "outlook_30d": result.get("outlook_30d"),
        "outlook_90d": result.get("outlook_90d"),
        "intelligence_gaps": result.get("intelligence_gaps", []),
        "confidence_level": result.get("confidence_level"),
    }

    if supabase:
        try:
            supabase.table("financial_risk_briefings").insert(briefing).execute()
        except Exception as e:
            briefing["supabase_warning"] = str(e)

    return {
        "engine": "financial_risk_command",
        "status": "success",
        "agent": "nemotron_financial_risk_agent",
        "model": NEMOTRON_MODEL,
        "result": briefing
    }


# ============================================================
# Country Financial Risk Record
# ============================================================

@router.get("/country/{country}")
def get_country_financial_risk(country: str):
    response = (
        require_supabase()
        .table("country_financial_risk_scores")
        .select("*")
        .ilike("country", country)
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    )

    return {
        "status": "success",
        "country": country,
        "data": response.data
    }


# ============================================================
# Financial Contagion Scenario Lab
# ============================================================

@router.post("/scenario")
def run_financial_contagion_scenario(payload: FinancialScenarioRequest):
    prompt = f"""
You are the Sovereign Intelligence Financial Contagion Lab.

Assess this financial shock scenario:

Country: {payload.country}
Shock type: {payload.shock_type}
Time horizon: {payload.time_horizon}
Exposure type: {payload.exposure_type}

Return ONLY valid JSON with this exact structure:

{{
  "first_order_impact": "",
  "second_order_effects": [],
  "regional_spillover": [],
  "market_implications": [],
  "fx_impact": "",
  "commodity_impact": "",
  "policy_response_options": [],
  "early_warning_indicators": [],
  "confidence_level": ""
}}
"""

    response = require_openai().chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a senior financial contagion and sovereign risk analyst. Return only valid JSON."
            },
            {
                "role": "user",
                "content": prompt
            },
        ],
        response_format={"type": "json_object"},
    )

    result = safe_json_loads(response.choices[0].message.content)

    scenario = {
        "country": payload.country,
        "shock_type": payload.shock_type,
        "time_horizon": payload.time_horizon,
        "exposure_type": payload.exposure_type,
        "first_order_impact": result.get("first_order_impact"),
        "second_order_effects": result.get("second_order_effects", []),
        "regional_spillover": result.get("regional_spillover", []),
        "market_implications": result.get("market_implications", []),
        "fx_impact": result.get("fx_impact"),
        "commodity_impact": result.get("commodity_impact"),
        "policy_response_options": result.get("policy_response_options", []),
        "early_warning_indicators": result.get("early_warning_indicators", []),
        "confidence_level": result.get("confidence_level"),
    }

    if supabase:
        try:
            supabase.table("financial_contagion_scenarios").insert(scenario).execute()
        except Exception as e:
            scenario["supabase_warning"] = str(e)

    return {
        "engine": "financial_contagion_lab",
        "status": "success",
        "result": scenario
    }


# ============================================================
# Stored Briefings
# ============================================================

@router.get("/briefings")
def get_recent_financial_briefings(limit: int = Query(10, ge=1, le=50)):
    response = (
        require_supabase()
        .table("financial_risk_briefings")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return {
        "status": "success",
        "count": len(response.data),
        "data": response.data
    }


# ============================================================
# Fusion Endpoint: OpenAI + Nemotron
# ============================================================

@router.post("/run-fusion-agent")
def run_financial_risk_fusion_agent(payload: FinancialRiskRequest):
    country = payload.country.strip()
    query = payload.query or f"{country} sovereign debt currency inflation banking sanctions financial risk"

    news_items = fetch_news_signals(query, 10)

    openai_result = generate_openai_financial_brief(country, query, news_items)

    nemotron_result = None
    nemotron_error = None

    if nemotron_client:
        try:
            nemotron_result = generate_nemotron_financial_brief(country, query, news_items)
        except Exception as e:
            nemotron_error = str(e)

    openai_score = normalize_score(openai_result.get("financial_risk_score"), 50)
    nemotron_score = normalize_score(nemotron_result.get("financial_risk_score"), openai_score) if nemotron_result else openai_score

    fused_score = round((openai_score + nemotron_score) / 2)

    fusion_briefing = {
        "country": country,
        "query": query,
        "executive_judgment": openai_result.get("executive_judgment"),
        "financial_risk_score": fused_score,
        "risk_level": risk_level(fused_score),
        "main_drivers": openai_result.get("main_drivers", []),
        "key_indicators": openai_result.get("key_indicators", []),
        "market_implications": openai_result.get("market_implications", []),
        "corporate_exposure": openai_result.get("corporate_exposure", []),
        "investor_implications": openai_result.get("investor_implications", []),
        "early_warning_indicators": openai_result.get("early_warning_indicators", []),
        "outlook_30d": openai_result.get("outlook_30d"),
        "outlook_90d": openai_result.get("outlook_90d"),
        "intelligence_gaps": openai_result.get("intelligence_gaps", []),
        "confidence_level": openai_result.get("confidence_level"),
    }

    if supabase:
        try:
            supabase.table("financial_risk_briefings").insert(fusion_briefing).execute()
        except Exception as e:
            fusion_briefing["supabase_warning"] = str(e)

    return {
        "engine": "financial_risk_fusion_command",
        "status": "success",
        "agent": "openai_nemotron_financial_fusion_agent",
        "models": {
            "openai": OPENAI_MODEL,
            "nemotron": NEMOTRON_MODEL if nemotron_client else None
        },
        "scores": {
            "openai_score": openai_score,
            "nemotron_score": nemotron_score if nemotron_result else None,
            "fused_score": fused_score
        },
        "nemotron_error": nemotron_error,
        "result": fusion_briefing,
        "model_outputs": {
            "openai": openai_result,
            "nemotron": nemotron_result
        }
    }
