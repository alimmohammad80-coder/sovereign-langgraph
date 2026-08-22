from typing import Dict, Any, List
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import os
import json

load_dotenv(dotenv_path=Path(".env"))

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_MODEL = os.getenv("NVIDIA_ULTRA_MODEL") or os.getenv("NVIDIA_MODEL") or "nvidia/nemotron-3-ultra-550b-a55b"


def nemotron_configured() -> bool:
    return bool(NVIDIA_API_KEY)


def run_nemotron_country_reasoning(
    country_name: str,
    risk_score: int,
    risk_level: str,
    scores: Dict[str, Any],
    signals: List[Dict[str, Any]],
    convergence: Dict[str, Any],
    timeframe: str = "30 days"
) -> Dict[str, Any]:
    if not nemotron_configured():
        return {
            "status": "unavailable",
            "model_used": "country_intelligence_v1_signals"
        }

    client = OpenAI(
        base_url=NVIDIA_BASE_URL,
        api_key=NVIDIA_API_KEY
    )

    prompt = f"""
You are Sovereign Intelligence AI, producing country intelligence for decision-makers.

Country: {country_name}
Timeframe: {timeframe}
Analyst risk score: {risk_score}/100
Risk level: {risk_level}

Analyst scores:
{json.dumps(scores, indent=2, default=str)}

Live strategic signals:
{json.dumps(signals[:8], indent=2, default=str)}

Signal convergence:
{json.dumps(convergence, indent=2, default=str)}

Return strict JSON only:
{{
  "executive_judgment": "3-5 sentence IC-style BLUF",
  "risk_context": "strategic context, why it matters, second-order effects",
  "forecast": {{
    "7d": "...",
    "30d": "...",
    "90d": "..."
  }},
  "decision_support": [
    "specific action 1",
    "specific action 2",
    "specific action 3"
  ],
  "scenario_questions": [
    "scenario question 1",
    "scenario question 2",
    "scenario question 3"
  ]
}}

Do not use markdown.
Do not invent facts beyond provided signals and scores.
"""

    try:
        messages = [
            {
                "role": "system",
                "content": "You are a senior geopolitical intelligence analyst. Return valid JSON only."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        try:
            response = client.chat.completions.create(
                model=NVIDIA_MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=2000,
                extra_body={
                    "chat_template_kwargs": {
                        "enable_thinking": True
                    },
                    "reasoning_budget": 4096
                }
            )
        except Exception as primary_error:
            primary_error_text = str(primary_error)
            print(
                "[Country Intelligence] Nemotron reasoning call failed; "
                f"retrying without reasoning parameters: {primary_error_text}"
            )

            response = client.chat.completions.create(
                model=NVIDIA_MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=2000
            )

            print(
                "[Country Intelligence] Nemotron compatibility retry succeeded "
                f"with model {NVIDIA_MODEL}."
            )

        content = response.choices[0].message.content

        try:
            parsed = json.loads(content)
        except Exception:
            parsed = {
                "executive_judgment": content,
                "risk_context": "Nemotron returned non-JSON output.",
                "forecast": {},
                "decision_support": [],
                "scenario_questions": []
            }

        parsed["model_used"] = NVIDIA_MODEL
        return parsed

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "model_used": "country_intelligence_v1_signals"
        }
