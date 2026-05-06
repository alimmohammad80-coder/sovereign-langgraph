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


router = APIRouter(
    prefix="/api/corporate-exposure",
    tags=["Corporate Exposure & Portfolio Intelligence"]
)


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


supabase: Optional[Client] = None
openai_client: Optional[OpenAI] = None
nemotron_client: Optional[OpenAI] = None


if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("[Corporate Exposure] Supabase configured.")
    except Exception as e:
        print(f"[Corporate Exposure] Supabase client failed: {e}")
else:
    print("[Corporate Exposure] Supabase not configured.")


if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        print("[Corporate Exposure] OpenAI configured.")
    except Exception as e:
        print(f"[Corporate Exposure] OpenAI client failed: {e}")
else:
    print("[Corporate Exposure] OpenAI not configured.")


if NVIDIA_API_KEY:
    try:
        nemotron_client = OpenAI(
            base_url=NVIDIA_BASE_URL,
            api_key=NVIDIA_API_KEY
        )
        print("[Corporate Exposure] Nemotron configured.")
    except Exception as e:
        print(f"[Corporate Exposure] Nemotron client failed: {e}")
else:
    print("[Corporate Exposure] Nemotron not configured.")


class CorporateExposureRequest(BaseModel):
    company_name: str = Field(..., min_length=2)
    ticker: Optional[str] = None
    sector: Optional[str] = None
    country: Optional[str] = None
    query: Optional[str] = None


class PortfolioAnalyzeRequest(BaseModel):
    portfolio_name: str = Field("Strategic Portfolio", min_length=2)
    holdings: List[Dict[str, Any]] = Field(
        ...,
        description="List of holdings. Example: [{'ticker':'AAPL','company_name':'Apple','weight':15}]"
    )
    query: Optional[str] = None


class CorporateScenarioRequest(BaseModel):
    company_name: Optional[str] = None
    ticker: Optional[str] = None
    portfolio_name: Optional[str] = None
    holdings: Optional[List[Dict[str, Any]]] = None
    shock_type: str = Field(..., min_length=2)
    region: str = Field(..., min_length=2)
    time_horizon: str = Field(..., min_length=2)
    exposure_type: str = Field(..., min_length=2)


def require_openai() -> OpenAI:
    if not openai_client:
        raise HTTPException(
            status_code=500,
            detail="OpenAI is not configured. Add OPENAI_API_KEY to .env or Render."
        )
    return openai_client


def require_supabase() -> Client:
    if not supabase:
        raise HTTPException(
            status_code=500,
            detail="Supabase is not configured. Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
        )
    return supabase


def safe_json_loads(raw: str) -> Dict[str, Any]:
    try:
        return json.loads(raw)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail=f"Model returned invalid JSON: {raw[:500]}"
        )


def normalize_score(value: Any, fallback: int = 50) -> int:
    try:
        score = int(value)
        return max(0, min(100, score))
    except Exception:
        return fallback


def exposure_level(score: int) -> str:
    if score >= 76:
        return "severe"
    if score >= 56:
        return "high"
    if score >= 31:
        return "moderate"
    return "low"


@router.get("/health")
def corporate_exposure_health():
    return {
        "status": "ok",
        "module": "Corporate Exposure & Portfolio Intelligence",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/api-status")
def corporate_exposure_api_status():
    return {
        "status": "ok",
        "module": "Corporate Exposure & Portfolio Intelligence",
        "timestamp": datetime.utcnow().isoformat(),
        "supabase_configured": bool(SUPABASE_URL and SUPABASE_KEY and supabase),
        "openai_configured": bool(OPENAI_API_KEY and openai_client),
        "openai_model": OPENAI_MODEL,
        "nvidia_configured": bool(NVIDIA_API_KEY and nemotron_client),
        "nemotron_model": NEMOTRON_MODEL,
        "newsapi_configured": bool(NEWS_API_KEY)
    }


def fetch_corporate_signals(query: str, limit: int = 10) -> List[Dict[str, Any]]:
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
        return response.json().get("articles", [])
    except Exception as e:
        print(f"[Corporate Exposure] NewsAPI error: {e}")
        return []


@router.get("/live-signals")
def get_corporate_exposure_signals(
    query: str = Query("corporate exposure sanctions supply chain geopolitical financial risk"),
    limit: int = Query(10, ge=1, le=50)
):
    articles = fetch_corporate_signals(query, limit)
    signals = []

    for item in articles:
        if not isinstance(item, dict):
            continue

        signal = {
            "company_name": None,
            "ticker": None,
            "sector": None,
            "country": None,
            "signal_type": "corporate_exposure_news",
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
                supabase.table("corporate_exposure_signals").insert(signal).execute()
            except Exception as e:
                print(f"[Corporate Exposure] Signal insert warning: {e}")

    return {
        "status": "success",
        "source": "NewsAPI",
        "query": query,
        "count": len(signals),
        "signals": signals
    }


def generate_corporate_exposure_brief(payload: CorporateExposureRequest, news_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    news_context = "\n".join([
        f"- {item.get('title')} | {item.get('description')} | {item.get('url')}"
        for item in news_items
        if isinstance(item, dict) and item.get("title")
    ])

    prompt = f"""
You are the Sovereign Intelligence Corporate Exposure Agent.

Assess geopolitical, financial, sanctions, supply-chain, energy, currency, and market exposure for this company.

Company: {payload.company_name}
Ticker: {payload.ticker or "Unknown"}
Sector: {payload.sector or "Unknown"}
Country: {payload.country or "Unknown"}

User query:
{payload.query or "General corporate exposure assessment"}

Recent signal context:
{news_context or "No recent signal context available."}

Return ONLY valid JSON with this exact structure:

{{
  "executive_judgment": "",
  "exposure_score": 0,
  "exposure_level": "",
  "geographic_exposure": [],
  "sector_exposure": [],
  "sanctions_exposure": [],
  "supply_chain_exposure": [],
  "energy_exposure": [],
  "currency_exposure": [],
  "financial_exposure": [],
  "geopolitical_triggers": [],
  "early_warning_indicators": [],
  "mitigation_options": [],
  "intelligence_gaps": [],
  "confidence_level": ""
}}

Scoring:
0-30 low exposure
31-55 moderate exposure
56-75 high exposure
76-100 severe exposure

Make the output decision-grade for a corporate risk office, investor, or strategy team.
"""

    response = require_openai().chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a senior corporate geopolitical and financial exposure analyst. Return only valid JSON."
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
def run_corporate_exposure_agent(payload: CorporateExposureRequest):
    query = payload.query or f"{payload.company_name} sanctions supply chain geopolitical financial exposure risk"
    news_items = fetch_corporate_signals(query, 10)

    result = generate_corporate_exposure_brief(payload, news_items)

    score = normalize_score(result.get("exposure_score"), 50)
    level = result.get("exposure_level") or exposure_level(score)

    briefing = {
        "company_name": payload.company_name,
        "ticker": payload.ticker,
        "sector": payload.sector,
        "country": payload.country,
        "query": query,
        "exposure_score": score,
        "exposure_level": level,
        "executive_judgment": result.get("executive_judgment"),
        "geographic_exposure": result.get("geographic_exposure", []),
        "sector_exposure": result.get("sector_exposure", []),
        "sanctions_exposure": result.get("sanctions_exposure", []),
        "supply_chain_exposure": result.get("supply_chain_exposure", []),
        "energy_exposure": result.get("energy_exposure", []),
        "currency_exposure": result.get("currency_exposure", []),
        "financial_exposure": result.get("financial_exposure", []),
        "geopolitical_triggers": result.get("geopolitical_triggers", []),
        "early_warning_indicators": result.get("early_warning_indicators", []),
        "mitigation_options": result.get("mitigation_options", []),
        "intelligence_gaps": result.get("intelligence_gaps", []),
        "confidence_level": result.get("confidence_level"),
    }

    if supabase:
        try:
            supabase.table("corporate_exposure_briefings").insert(briefing).execute()
        except Exception as e:
            briefing["supabase_warning"] = str(e)

    return {
        "engine": "corporate_exposure_command",
        "status": "success",
        "agent": "corporate_exposure_agent",
        "model": OPENAI_MODEL,
        "result": briefing
    }


def generate_portfolio_intelligence(payload: PortfolioAnalyzeRequest, news_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    holdings_text = json.dumps(payload.holdings, indent=2)

    news_context = "\n".join([
        f"- {item.get('title')} | {item.get('description')} | {item.get('url')}"
        for item in news_items
        if isinstance(item, dict) and item.get("title")
    ])

    prompt = f"""
You are the Sovereign Intelligence Portfolio Intelligence Agent.

Assess the geopolitical, financial, sanctions, supply-chain, energy, currency, commodity, and market-risk exposure of this portfolio.

Portfolio name:
{payload.portfolio_name}

Holdings:
{holdings_text}

User query:
{payload.query or "General portfolio geopolitical and financial exposure assessment"}

Recent signal context:
{news_context or "No recent signal context available."}

Return ONLY valid JSON with this exact structure:

{{
  "executive_judgment": "",
  "portfolio_risk_score": 0,
  "risk_level": "",
  "highest_risk_holdings": [],
  "geographic_concentration": [],
  "sector_concentration": [],
  "sanctions_exposure": [],
  "supply_chain_exposure": [],
  "currency_exposure": [],
  "commodity_exposure": [],
  "geopolitical_scenario_exposure": [],
  "diversification_risks": [],
  "hedging_considerations": [],
  "early_warning_indicators": [],
  "recommended_monitoring_queries": [],
  "intelligence_gaps": [],
  "confidence_level": ""
}}

Scoring:
0-30 low portfolio risk
31-55 moderate portfolio risk
56-75 high portfolio risk
76-100 severe portfolio risk

Do not provide financial advice. Provide risk intelligence and decision-support analysis only.
"""

    response = require_openai().chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a senior portfolio geopolitical-risk and financial-exposure analyst. Return only valid JSON."
            },
            {
                "role": "user",
                "content": prompt
            },
        ],
        response_format={"type": "json_object"},
    )

    return safe_json_loads(response.choices[0].message.content)


@router.post("/portfolio-analyze")
def analyze_portfolio(payload: PortfolioAnalyzeRequest):
    tickers = " ".join([
        str(h.get("ticker") or h.get("company_name") or "")
        for h in payload.holdings
    ])

    query = payload.query or f"{tickers} sanctions supply chain geopolitical financial risk portfolio exposure"
    news_items = fetch_corporate_signals(query, 10)

    result = generate_portfolio_intelligence(payload, news_items)

    score = normalize_score(result.get("portfolio_risk_score"), 50)
    level = result.get("risk_level") or exposure_level(score)

    briefing = {
        "portfolio_name": payload.portfolio_name,
        "holdings": payload.holdings,
        "query": query,
        "portfolio_risk_score": score,
        "risk_level": level,
        "executive_judgment": result.get("executive_judgment"),
        "highest_risk_holdings": result.get("highest_risk_holdings", []),
        "geographic_concentration": result.get("geographic_concentration", []),
        "sector_concentration": result.get("sector_concentration", []),
        "sanctions_exposure": result.get("sanctions_exposure", []),
        "supply_chain_exposure": result.get("supply_chain_exposure", []),
        "currency_exposure": result.get("currency_exposure", []),
        "commodity_exposure": result.get("commodity_exposure", []),
        "geopolitical_scenario_exposure": result.get("geopolitical_scenario_exposure", []),
        "diversification_risks": result.get("diversification_risks", []),
        "hedging_considerations": result.get("hedging_considerations", []),
        "early_warning_indicators": result.get("early_warning_indicators", []),
        "recommended_monitoring_queries": result.get("recommended_monitoring_queries", []),
        "intelligence_gaps": result.get("intelligence_gaps", []),
        "confidence_level": result.get("confidence_level"),
    }

    if supabase:
        try:
            supabase.table("portfolio_intelligence_briefings").insert(briefing).execute()
        except Exception as e:
            briefing["supabase_warning"] = str(e)

    return {
        "engine": "portfolio_intelligence_command",
        "status": "success",
        "agent": "portfolio_intelligence_agent",
        "model": OPENAI_MODEL,
        "result": briefing
    }


@router.post("/scenario")
def run_corporate_exposure_scenario(payload: CorporateScenarioRequest):
    holdings_text = json.dumps(payload.holdings or [], indent=2)

    prompt = f"""
You are the Sovereign Intelligence Corporate Exposure Scenario Agent.

Assess this corporate or portfolio exposure scenario.

Company: {payload.company_name or "N/A"}
Ticker: {payload.ticker or "N/A"}
Portfolio: {payload.portfolio_name or "N/A"}
Holdings:
{holdings_text}

Shock type: {payload.shock_type}
Region: {payload.region}
Time horizon: {payload.time_horizon}
Exposure type: {payload.exposure_type}

Return ONLY valid JSON with this exact structure:

{{
  "first_order_impact": "",
  "second_order_effects": [],
  "affected_holdings": [],
  "affected_sectors": [],
  "affected_regions": [],
  "market_implications": [],
  "operational_implications": [],
  "supply_chain_implications": [],
  "financial_implications": [],
  "mitigation_options": [],
  "early_warning_indicators": [],
  "confidence_level": ""
}}
"""

    response = require_openai().chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a senior corporate and portfolio scenario-risk analyst. Return only valid JSON."
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
        "company_name": payload.company_name,
        "ticker": payload.ticker,
        "portfolio_name": payload.portfolio_name,
        "shock_type": payload.shock_type,
        "region": payload.region,
        "time_horizon": payload.time_horizon,
        "exposure_type": payload.exposure_type,
        "first_order_impact": result.get("first_order_impact"),
        "second_order_effects": result.get("second_order_effects", []),
        "affected_holdings": result.get("affected_holdings", []),
        "affected_sectors": result.get("affected_sectors", []),
        "affected_regions": result.get("affected_regions", []),
        "market_implications": result.get("market_implications", []),
        "operational_implications": result.get("operational_implications", []),
        "supply_chain_implications": result.get("supply_chain_implications", []),
        "financial_implications": result.get("financial_implications", []),
        "mitigation_options": result.get("mitigation_options", []),
        "early_warning_indicators": result.get("early_warning_indicators", []),
        "confidence_level": result.get("confidence_level"),
    }

    if supabase:
        try:
            supabase.table("corporate_exposure_scenarios").insert(scenario).execute()
        except Exception as e:
            scenario["supabase_warning"] = str(e)

    return {
        "engine": "corporate_exposure_scenario_lab",
        "status": "success",
        "result": scenario
    }


@router.get("/briefings")
def get_corporate_exposure_briefings(limit: int = Query(10, ge=1, le=50)):
    corporate_data = []
    portfolio_data = []

    if supabase:
        try:
            corporate_data = (
                supabase.table("corporate_exposure_briefings")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
                .data
            )
        except Exception as e:
            print(f"[Corporate Exposure] Corporate briefings warning: {e}")

        try:
            portfolio_data = (
                supabase.table("portfolio_intelligence_briefings")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
                .data
            )
        except Exception as e:
            print(f"[Corporate Exposure] Portfolio briefings warning: {e}")

    return {
        "status": "success",
        "corporate_count": len(corporate_data),
        "portfolio_count": len(portfolio_data),
        "corporate_briefings": corporate_data,
        "portfolio_briefings": portfolio_data
    }
