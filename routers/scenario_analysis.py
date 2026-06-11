from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client
import os
import json

load_dotenv(dotenv_path=Path(".env"))

router = APIRouter(prefix="/api/scenario-analysis", tags=["Scenario Analysis"])

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_MODEL = os.getenv("NVIDIA_SCENARIO_MODEL") or os.getenv("NVIDIA_ULTRA_MODEL") or os.getenv("NVIDIA_MODEL") or "nvidia/nemotron-3-ultra-550b-a55b"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_SCENARIO_MODEL = os.getenv("OPENAI_SCENARIO_MODEL", "gpt-4.1")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None


class ScenarioAnalysisRequest(BaseModel):
    scenario: str
    country: Optional[str] = None
    iso3: Optional[str] = None
    region: Optional[str] = None
    time_horizon: str = "30 days"
    source_module: Optional[str] = "manual"
    source_context: Optional[Dict[str, Any]] = None


def load_latest_country_context(country: Optional[str] = None, iso3: Optional[str] = None):
    if not supabase:
        return None

    try:
        q = (
            supabase.table("report_context_memory")
            .select("*")
            .eq("source_module", "country_intelligence")
        )

        if iso3:
            q = q.eq("iso3", iso3.upper())
        elif country:
            q = q.eq("country_name", country)

        res = q.order("created_at", desc=True).limit(1).execute()
        if res.data:
            return res.data[0].get("context_payload")
    except Exception:
        return None

    return None


def build_prompt(payload: ScenarioAnalysisRequest):
    context = payload.source_context or {}

    compact_context = {
        "country_name": context.get("country_name"),
        "iso3": context.get("iso3"),
        "risk_level": context.get("risk_level"),
        "risk_score": context.get("risk_score"),
        "executive_judgment": context.get("executive_judgment"),
        "risk_context": context.get("risk_context"),
        "forecast": context.get("forecast"),
        "signal_convergence": context.get("signal_convergence"),
        "strategic_signals": (context.get("strategic_signals") or [])[:5],
    }

    return f"""
You are Sovereign Intelligence AI, a strategic foresight engine.

Write a forward-looking scenario analysis for senior decision-makers.

Scenario:
{payload.scenario}

Country:
{payload.country}

Time horizon:
{payload.time_horizon}

Relevant country intelligence context:
{json.dumps(compact_context, indent=2, default=str)}

Return STRICT JSON only:
{{
  "title": "",
  "executive_judgment": "",
  "strategic_outlook": "",
  "watch_indicators": [],
  "recommended_actions": []
}}

Rules:
- Total report should be no more than 500 words.
- No scoring.
- No risk meters.
- No dashboard language.
- Use only 3 main written sections: executive_judgment, strategic_outlook, recommended_actions.
- executive_judgment: 100-140 words.
- strategic_outlook: 250-320 words.
- watch_indicators: 3-5 concise indicators.
- recommended_actions: 3 concise strategic actions.
- Write as a serious geopolitical foresight assessment.
- Do not use numbered lists inside strategic_outlook.
- strategic_outlook must be one flowing narrative paragraph.
- Avoid generic phrases like significant risks, far-reaching consequences, or monitor closely.
- Focus on what happens next, escalation logic, second-order effects, and decision implications.
- Do not use markdown.
"""


def fallback_scenario(payload: ScenarioAnalysisRequest):
    return {
        "title": f"Scenario Analysis: {payload.country or 'Selected Country'}",
        "executive_judgment": f"The scenario '{payload.scenario}' requires forward-looking assessment using the latest country intelligence context.",
        "strategic_outlook": "The scenario presents potential escalation pathways that should be assessed through political, economic, security, and regional spillover dynamics. Immediate attention should focus on whether the triggering condition remains isolated or begins to interact with wider strategic pressures. If multiple domains converge, the scenario could move from a contained disruption to a broader strategic risk environment.",
        "watch_indicators": [
            "Leadership statements and red-line signaling",
            "Military or security force posture changes",
            "Market or currency stress",
            "Diplomatic mediation activity"
        ],
        "recommended_actions": [
            "Monitor leading indicators daily.",
            "Prepare contingency options for escalation and stabilization pathways.",
            "Run a follow-up scenario if trigger indicators intensify."
        ],
        "model_used": "fallback_scenario_analysis",
        "generated_at": datetime.utcnow().isoformat()
    }


def run_model(payload: ScenarioAnalysisRequest):
    prompt = build_prompt(payload)

    if OPENAI_API_KEY:
        try:
            client = OpenAI(api_key=OPENAI_API_KEY, timeout=75.0)
            response = client.chat.completions.create(
                model=OPENAI_SCENARIO_MODEL,
                messages=[
                    {"role": "system", "content": "Return valid JSON only. You are a strategic foresight analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=1400
            )
            content = response.choices[0].message.content
            data = json.loads(content)
            data["model_used"] = OPENAI_SCENARIO_MODEL
            data["provider"] = "openai"
            data["generated_at"] = datetime.utcnow().isoformat()
            return data
        except Exception as e:
            openai_error = str(e)
    else:
        openai_error = "OPENAI_API_KEY not configured"

    if NVIDIA_API_KEY:
        try:
            client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY, timeout=75.0)
            response = client.chat.completions.create(
                model=NVIDIA_MODEL,
                messages=[
                    {"role": "system", "content": "Return valid JSON only. You are a strategic foresight analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=900,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}}
            )
            content = response.choices[0].message.content
            data = json.loads(content)
            data["model_used"] = NVIDIA_MODEL
            data["provider"] = "nvidia"
            data["generated_at"] = datetime.utcnow().isoformat()
            return data
        except Exception as e:
            data = fallback_scenario(payload)
            data["openai_error"] = openai_error
            data["nvidia_error"] = str(e)
            return data

    data = fallback_scenario(payload)
    data["openai_error"] = openai_error
    return data


@router.get("/health")
def health():
    return {
        "status": "ok",
        "module": "scenario_analysis",
        "openai_configured": bool(OPENAI_API_KEY),
        "nemotron_configured": bool(NVIDIA_API_KEY),
        "supabase_configured": bool(supabase),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/run")
def run_scenario_analysis(payload: ScenarioAnalysisRequest):
    if not payload.source_context:
        latest_context = load_latest_country_context(country=payload.country, iso3=payload.iso3)
        if latest_context:
            payload.source_context = latest_context

    data = run_model(payload)

    return {
        "status": "success",
        "data": data
    }
