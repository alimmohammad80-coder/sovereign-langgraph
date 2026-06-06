from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import os
import json

load_dotenv(dotenv_path=Path(".env"))

router = APIRouter(prefix="/api/scenario-analysis", tags=["Scenario Analysis"])

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_MODEL = os.getenv("NVIDIA_ULTRA_MODEL") or os.getenv("NVIDIA_MODEL") or "nvidia/nemotron-3-ultra-550b-a55b"


class ScenarioAnalysisRequest(BaseModel):
    scenario: str
    country: Optional[str] = None
    region: Optional[str] = None
    time_horizon: str = "30 days"
    source_module: Optional[str] = "manual"
    source_context: Optional[Dict[str, Any]] = None


def fallback_scenario(payload: ScenarioAnalysisRequest):
    return {
        "executive_summary": f"Scenario analysis for: {payload.scenario}",
        "risk_level": "Elevated",
        "confidence": 65,
        "baseline_conditions": [
            "Baseline conditions require additional live context.",
            "Assessment is based on the submitted scenario question."
        ],
        "escalation_pathways": [
            "Gradual escalation through political and economic pressure.",
            "Rapid escalation if military, financial, or social stability triggers converge.",
            "De-escalation if diplomatic or market stabilizers intervene."
        ],
        "second_order_effects": [
            "Market volatility",
            "Policy uncertainty",
            "Regional spillover risk"
        ],
        "decision_options": [
            "Monitor leading indicators closely.",
            "Prepare contingency plans.",
            "Run follow-up scenarios for worst-case and best-case outcomes."
        ],
        "timeline": {
            "7d": "Watch for immediate trigger events.",
            "30d": "Assess whether signals converge or stabilize.",
            "90d": "Evaluate structural impact and policy response."
        },
        "model_used": "fallback_scenario_analysis"
    }


@router.get("/health")
def health():
    return {
        "status": "ok",
        "module": "scenario_analysis",
        "nemotron_configured": bool(NVIDIA_API_KEY),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/run")
def run_scenario_analysis(payload: ScenarioAnalysisRequest):
    if not NVIDIA_API_KEY:
        return {
            "status": "success",
            "data": fallback_scenario(payload)
        }

    prompt = f"""
You are Sovereign Intelligence AI running a strategic scenario simulation.

Scenario:
{payload.scenario}

Country:
{payload.country}

Region:
{payload.region}

Time Horizon:
{payload.time_horizon}

Source Module:
{payload.source_module}

Source Context:
{json.dumps(payload.source_context or {}, indent=2, default=str)}

Return strict JSON only with this structure:
{{
  "executive_summary": "clear 4-6 sentence scenario assessment",
  "risk_level": "Low | Guarded | Elevated | High | Critical",
  "confidence": 0,
  "baseline_conditions": [
    "condition 1",
    "condition 2",
    "condition 3"
  ],
  "escalation_pathways": [
    "pathway 1",
    "pathway 2",
    "pathway 3"
  ],
  "second_order_effects": [
    "effect 1",
    "effect 2",
    "effect 3"
  ],
  "cross_module_impacts": {{
    "supply_chain": "...",
    "financial_risk": "...",
    "early_warning": "...",
    "country_intelligence": "..."
  }},
  "decision_options": [
    "action 1",
    "action 2",
    "action 3"
  ],
  "timeline": {{
    "7d": "...",
    "30d": "...",
    "90d": "..."
  }},
  "watch_indicators": [
    "indicator 1",
    "indicator 2",
    "indicator 3"
  ]
}}

Do not use markdown.
Do not invent exact facts not provided in context.
Be strategic, practical, and decision-support oriented.
"""

    try:
        client = OpenAI(
            base_url=NVIDIA_BASE_URL,
            api_key=NVIDIA_API_KEY,
            timeout=45.0
        )

        response = client.chat.completions.create(
            model=NVIDIA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a senior geopolitical scenario analyst. Return valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.25,
            max_tokens=1200,
            extra_body={
                "chat_template_kwargs": {
                    "enable_thinking": False
                }
            }
        )

        content = response.choices[0].message.content

        try:
            data = json.loads(content)
        except Exception:
            data = fallback_scenario(payload)
            data["raw_model_output"] = content

        data["model_used"] = NVIDIA_MODEL
        data["generated_at"] = datetime.utcnow().isoformat()

        return {
            "status": "success",
            "data": data
        }

    except Exception as e:
        data = fallback_scenario(payload)
        data["error"] = str(e)
        return {
            "status": "success",
            "data": data
        }
