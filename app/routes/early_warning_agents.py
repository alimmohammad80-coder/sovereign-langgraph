from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import json
import hashlib

try:
    from supabase import create_client
except Exception as e:
    create_client = None
    print(f"[EWS Agents] Supabase import unavailable: {e}")

try:
    from google import genai
except Exception as e:
    genai = None
    print(f"[EWS Agents] Gemini import unavailable: {e}")


router = APIRouter(
    prefix="/api/early-warning/agents",
    tags=["Strategic Early Warning Agentic Mesh"]
)


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

supabase = (
    create_client(SUPABASE_URL, SUPABASE_KEY)
    if create_client and SUPABASE_URL and SUPABASE_KEY
    else None
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_SIFTER_MODEL = os.getenv("GEMINI_SIFTER_MODEL", "gemini-3-flash-lite-preview")
GEMINI_ANALYST_MODEL = os.getenv("GEMINI_ANALYST_MODEL", "gemini-3.1-pro-preview")

gemini_client = (
    genai.Client(api_key=GEMINI_API_KEY)
    if genai and GEMINI_API_KEY
    else None
)

if gemini_client:
    print("[EWS Agents] Gemini configured.")
else:
    print("[EWS Agents] Gemini not configured or unavailable.")

if supabase:
    print("[EWS Agents] Supabase configured.")
else:
    print("[EWS Agents] Supabase not configured or unavailable.")

class RawSignal(BaseModel):
    source: Optional[str] = "unknown"
    title: str
    summary: Optional[str] = ""
    url: Optional[str] = None
    domain: Optional[str] = None
    published_at: Optional[str] = None


class SiftRequest(BaseModel):
    domain: Optional[str] = "geopolitical_conflict"
    query: Optional[str] = None
    items: List[RawSignal]


class DeepAssessRequest(BaseModel):
    sifted_signal_id: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    topic: Optional[str] = None
    include_red_team: Optional[bool] = True
    include_grounding: Optional[bool] = False
    sifter_output: Optional[Dict[str, Any]] = None

class SiftRequest(BaseModel):
    domain: Optional[str] = "geopolitical_conflict"
    query: Optional[str] = None
    items: List[RawSignal]


def content_hash(title: str, url: Optional[str]) -> str:
    base = f"{title.strip().lower()}::{url or ''}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def safe_json_parse(text: str) -> Dict[str, Any]:
    if not text:
        return {
            "status": "error",
            "message": "Empty model output.",
        }

    cleaned = text.strip()

    # Remove markdown code fences
    if cleaned.startswith("```json"):
        cleaned = cleaned[len("```json"):].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned[len("```"):].strip()

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    # Extract first JSON object if extra text exists
    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start:end + 1]

    try:
        return json.loads(cleaned)
    except Exception as e:
        return {
            "status": "unparsed_output",
            "message": "Model output could not be parsed as JSON.",
            "parse_error": str(e),
            "raw_text": text,
        }

def save_raw_signal(item: RawSignal, query: Optional[str]) -> Optional[str]:
    if not supabase:
        return None

    try:
        signal_hash = content_hash(item.title, item.url)

        payload = {
            "source": item.source,
            "title": item.title,
            "summary": item.summary,
            "url": item.url,
            "domain": item.domain,
            "published_at": item.published_at,
            "query": query,
            "content_hash": signal_hash,
        }

        response = (
            supabase.table("ews_raw_signals")
            .upsert(payload, on_conflict="content_hash")
            .execute()
        )

        if response.data:
            return response.data[0]["id"]

        return None

    except Exception as e:
        print(f"[EWS Agents] save_raw_signal error: {e}")
        return None


def save_sifted_signal(
    raw_signal_id: Optional[str],
    model_output: Dict[str, Any],
    model_used: str
) -> Optional[str]:
    if not supabase:
        return None

    try:
        payload = {
            "raw_signal_id": raw_signal_id,
            "is_relevant": bool(model_output.get("is_relevant", False)),
            "domain": model_output.get("domain"),
            "signal_classification": model_output.get("signal_classification"),
            "confidence_score": int(model_output.get("confidence_score", 0) or 0),
            "severity_level": int(model_output.get("severity_level", 1) or 1),
            "country_or_region": model_output.get("country_or_region"),
            "bottom_line": model_output.get("bottom_line"),
            "so_what": model_output.get("so_what"),
            "affected_domains": model_output.get("affected_domains", []),
            "monitoring_indicators": model_output.get("monitoring_indicators", []),
            "counter_indicators": model_output.get("counter_indicators", []),
            "verification_required": bool(model_output.get("verification_required", False)),
            "recommended_action": model_output.get("recommended_action"),
            "model_used": model_used,
            "raw_model_output": model_output,
        }

        response = (
            supabase.table("ews_sifted_signals")
            .insert(payload)
            .execute()
        )

        if response.data:
            return response.data[0]["id"]

        return None

    except Exception as e:
        print(f"[EWS Agents] save_sifted_signal error: {e}")
        return None


def build_geopolitical_conflict_instruction() -> str:
    return """
You are the Senior Geopolitical & Conflict Intelligence Officer for Sovereign Intelligence.

Your mission is not to summarize news. Your mission is to identify early warning signals of conflict, instability, political violence, coercion, military escalation, or sovereign-risk deterioration.

Analytical Method:
1. Separate signal from noise.
   - Noise includes routine rhetoric, scheduled diplomatic meetings, generic commentary, repeated low-value headlines, and isolated claims without corroboration.
   - Signal includes troop movement, mobilization, border closure, kinetic activity, missile/drone activity, cyberattacks on critical infrastructure, emergency decrees, sanctions escalation, port disruption, elite fragmentation, mass unrest, or credible multi-source reporting.

2. Assess escalation relevance.
   Determine whether the item may affect security, energy, supply chains, finance, cyber/information operations, corporate exposure, or diplomatic posture within the next 48–72 hours.

3. Identify second-order effects.
   If relevant, explain likely spillovers into markets, energy, logistics, insurance, currency, sanctions, corporate operations, or regional stability.

4. Apply structured scoring.
   Return:
   - is_relevant
   - signal_classification
   - confidence_score from 0 to 100
   - severity_level from 1 to 10
   - time_horizon
   - escalation_probability
   - affected_domains
   - monitoring_indicators
   - counter_indicators
   - verification_required
   - recommended_action

Rules:
- Do not provide generic summaries.
- Do not invent facts.
- If evidence is weak, say so.
- If the item requires verification, mark verification_required as true.
- Focus on implications for the next 48–72 hours.
- Return valid JSON only.
"""


def local_fallback_sifter(item: RawSignal) -> Dict[str, Any]:
    text = f"{item.title} {item.summary}".lower()

    high_terms = [
        "attack", "missile", "drone", "troop", "mobilization", "border",
        "explosion", "airstrike", "sanctions", "blockade", "port closure",
        "tanker", "cyberattack", "coup", "riot", "protest", "clashes"
    ]

    medium_terms = [
        "warning", "threat", "tension", "dispute", "military", "naval",
        "diplomatic", "energy", "oil", "shipping", "currency", "election"
    ]

    hits = sum(1 for term in high_terms if term in text)
    medium_hits = sum(1 for term in medium_terms if term in text)

    score = min(100, hits * 18 + medium_hits * 8 + 20)

    if score >= 75:
        classification = "High Signal"
        severity = 8
    elif score >= 55:
        classification = "Emerging Signal"
        severity = 6
    elif score >= 35:
        classification = "Weak Signal"
        severity = 4
    else:
        classification = "Noise"
        severity = 1

    return {
        "is_relevant": score >= 35,
        "signal_classification": classification,
        "domain": "Geopolitical & Conflict",
        "country_or_region": None,
        "confidence_score": score,
        "severity_level": severity,
        "time_horizon": "48-72 hours",
        "escalation_probability": "Medium" if score >= 55 else "Low",
        "bottom_line": item.title,
        "so_what": "This item may require monitoring if corroborated by independent sources.",
        "affected_domains": ["Security"],
        "monitoring_indicators": [
            "Repeated reporting from independent sources",
            "Official confirmation",
            "Operational movement or physical disruption",
        ],
        "counter_indicators": [
            "Diplomatic de-escalation",
            "No operational activity",
            "Single-source reporting only",
        ],
        "verification_required": score >= 55,
        "recommended_action": "Monitor and corroborate before escalation.",
    }


def run_gemini_sifter(item: RawSignal, domain: str) -> Dict[str, Any]:
    if not gemini_client:
        return local_fallback_sifter(item)

    instruction = build_geopolitical_conflict_instruction()

    prompt = f"""
SYSTEM INSTRUCTION:
{instruction}

DOMAIN:
{domain}

RAW SIGNAL:
Source: {item.source}
Title: {item.title}
Summary: {item.summary}
URL: {item.url}
Published At: {item.published_at}

Return exactly one valid JSON object with these keys:
{{
  "is_relevant": true,
  "signal_classification": "Noise | Weak Signal | Emerging Signal | High Signal | Verified Alert Candidate",
  "domain": "Geopolitical & Conflict",
  "country_or_region": "string or null",
  "confidence_score": 0,
  "severity_level": 1,
  "time_horizon": "48-72 hours",
  "escalation_probability": "Low | Medium | High",
  "bottom_line": "string",
  "so_what": "string",
  "affected_domains": ["Security", "Energy", "Finance", "Supply Chain", "Cyber", "Political"],
  "monitoring_indicators": ["string"],
  "counter_indicators": ["string"],
  "verification_required": false,
  "recommended_action": "string"
}}
"""

    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_SIFTER_MODEL,
            contents=prompt,
        )

        raw_text = response.text or ""
        parsed = safe_json_parse(raw_text)

        parsed["model_provider"] = "Google Gemini"
        parsed["model_used"] = GEMINI_SIFTER_MODEL

        return parsed

    except Exception as e:
        print(f"[EWS Agents] Gemini sifter error: {e}")
        fallback = local_fallback_sifter(item)
        fallback["model_provider"] = "local_fallback"
        fallback["model_used"] = "local_rule_sifter"
        fallback["model_error"] = str(e)
        return fallback

def run_gemini_deep_assessment(
    country: Optional[str],
    region: Optional[str],
    topic: Optional[str],
    sifter_output: Dict[str, Any],
    include_red_team: bool = True,
    include_grounding: bool = False,
) -> Dict[str, Any]:
    if not gemini_client:
        return {
            "status": "unavailable",
            "provider": "local_fallback",
            "model_used": "none",
            "message": "Gemini is not configured.",
        }

    prompt = f"""
You are the Senior Strategic Intelligence Analyst for Sovereign Intelligence.

Mission:
Turn a high-signal early warning item into a professional intelligence assessment.

Do not summarize news. Produce intelligence judgment.

Context:
Country: {country}
Region: {region}
Topic: {topic}

Sifter Output:
{sifter_output}

Analytical Requirements:
1. Validate whether the signal is strategically meaningful.
2. Identify the likely 48-72 hour implications.
3. Build a ripple-effect chain across security, energy, finance, supply chain, cyber/information, and political stability.
4. Produce three scenario paths:
   - Status Quo
   - Escalation
   - De-escalation
5. If red team is enabled, challenge the assessment and identify counter-evidence.
6. If grounding is requested, mark what must be externally verified.

Important scoring rules:

- warning_score must be 0–100.

- confidence_score must be 0–100.

- vulnerability_index must be 0–100.

- severity is not requested in this deep assessment.

- Do not confuse severity_level 1–10 from the sifter with warning_score 0–100.


Return valid JSON only with exactly these keys:
{{
  "status": "success",
  "analyst_bottom_line": "string",
  "risk_level": "Low | Watch | Elevated | High | Critical",
  "warning_score": 0,
  "confidence_score": 0,
  "vulnerability_index": 0,
  "so_what": "string",
  "ripple_effects": [
    {{
      "stage": "Trigger | Primary Impact | Cross-Domain Spillover | Decision Consequence",
      "assessment": "string"
    }}
  ],
  "scenario_tree": [
    {{
      "scenario": "Status Quo | Escalation | De-escalation",
      "probability": "Low | Medium | High",
      "impact": "Low | Moderate | High | Severe",
      "description": "string",
      "trigger_indicators": ["string"]
    }}
  ],
  "red_team_challenge": {{
    "enabled": true,
    "counter_evidence": ["string"],
    "false_positive_risks": ["string"],
    "confidence_adjustment": "string"
  }},
  "priority_indicators_24h": ["string"],
  "exposed_domains": ["Security", "Energy", "Finance", "Supply Chain", "Cyber", "Political", "Corporate Exposure"],
  "recommended_actions": ["string"],
  "verification": {{
    "grounding_requested": false,
    "verification_required": true,
    "sources_to_check": ["Reuters", "AP", "official government statements", "maritime advisories", "market data"]
  }},
  "executive_brief": {{
    "tldr": "string",
    "key_judgments": ["string"],
    "monitoring_priorities": ["string"],
    "decision_relevance": "string"
  }}
}}
"""

    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_ANALYST_MODEL,
            contents=prompt,
        )

        raw_text = response.text or ""
        parsed = safe_json_parse(raw_text)

        # Normalize warning_score if model mistakenly returns 1–10 scale.
        try:
            warning_score = int(parsed.get("warning_score", 0) or 0)
            if 1 <= warning_score <= 10:
                parsed["warning_score"] = warning_score * 10
        except Exception:
            parsed["warning_score"] = 0

        try:
            confidence_score = int(parsed.get("confidence_score", 0) or 0)
            parsed["confidence_score"] = max(0, min(confidence_score, 100))
        except Exception:
            parsed["confidence_score"] = 0

        try:
            vulnerability_index = int(parsed.get("vulnerability_index", 0) or 0)
            parsed["vulnerability_index"] = max(0, min(vulnerability_index, 100))
        except Exception:
            parsed["vulnerability_index"] = 0

        parsed["provider"] = "Google Gemini"
        parsed["model_used"] = GEMINI_ANALYST_MODEL
        parsed["include_red_team"] = include_red_team
        parsed["include_grounding"] = include_grounding

        return parsed

    except Exception as e:
        print(f"[EWS Agents] Gemini deep assessment error: {e}")
        return {
            "status": "error",
            "provider": "Google Gemini",
            "model_used": GEMINI_ANALYST_MODEL,
            "error": str(e),
        }

@router.get("/health")
def ews_agents_health():
    return {
        "status": "online",
        "module": "EWS Agentic Mesh",
        "gemini_configured": True if gemini_client else False,
        "supabase_configured": True if supabase else False,
        "sifter_model": GEMINI_SIFTER_MODEL,
        "analyst_model": GEMINI_ANALYST_MODEL,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/sift")
def sift_signals(request: SiftRequest):
    results = []

    # Hard safety limit for Render memory.
    items = request.items[:25]

    for item in items:
        raw_signal_id = save_raw_signal(item, request.query)

        model_output = run_gemini_sifter(
            item=item,
            domain=request.domain or "geopolitical_conflict"
        )

        sifted_signal_id = save_sifted_signal(
            raw_signal_id=raw_signal_id,
            model_output=model_output,
            model_used=model_output.get("model_used", GEMINI_SIFTER_MODEL),
        )

        results.append({
            "raw_signal_id": raw_signal_id,
            "sifted_signal_id": sifted_signal_id,
            "input": item.model_dump(),
            "sifter_output": model_output,
        })

    high_signal_count = len([
        r for r in results
        if r["sifter_output"].get("signal_classification") in [
            "Emerging Signal",
            "High Signal",
            "Verified Alert Candidate"
        ]
    ])

    return {
        "status": "success",
        "architecture": "Agentic Mesh Phase 1",
        "agent": "Geopolitical & Conflict Sifter",
        "items_received": len(request.items),
        "items_processed": len(items),
        "high_signal_count": high_signal_count,
        "results": results,
    }

@router.post("/deep-assess")
def deep_assess_signal(request: DeepAssessRequest):
    sifter_output = request.sifter_output

    if not sifter_output and request.sifted_signal_id and supabase:
        try:
            response = (
                supabase.table("ews_sifted_signals")
                .select("*")
                .eq("id", request.sifted_signal_id)
                .limit(1)
                .execute()
            )

            if response.data:
                row = response.data[0]
                sifter_output = row.get("raw_model_output") or {
                    "is_relevant": row.get("is_relevant"),
                    "signal_classification": row.get("signal_classification"),
                    "domain": row.get("domain"),
                    "country_or_region": row.get("country_or_region"),
                    "confidence_score": row.get("confidence_score"),
                    "severity_level": row.get("severity_level"),
                    "bottom_line": row.get("bottom_line"),
                    "so_what": row.get("so_what"),
                    "affected_domains": row.get("affected_domains"),
                    "monitoring_indicators": row.get("monitoring_indicators"),
                    "counter_indicators": row.get("counter_indicators"),
                    "verification_required": row.get("verification_required"),
                    "recommended_action": row.get("recommended_action"),
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Could not load sifted signal from Supabase: {str(e)}",
            }

    if not sifter_output:
        return {
            "status": "error",
            "message": "Provide either sifter_output or sifted_signal_id.",
        }

    assessment = run_gemini_deep_assessment(
        country=request.country,
        region=request.region,
        topic=request.topic,
        sifter_output=sifter_output,
        include_red_team=request.include_red_team,
        include_grounding=request.include_grounding,
    )

    verified_alert_id = None

    if supabase and assessment.get("status") == "success":
        try:
            payload = {
                "sifted_signal_id": request.sifted_signal_id,
                "country": request.country,
                "region": request.region,
                "topic": request.topic,
                "risk_level": assessment.get("risk_level"),
                "warning_score": assessment.get("warning_score"),
                "confidence_score": assessment.get("confidence_score"),
                "vulnerability_index": assessment.get("vulnerability_index"),
                "bottom_line": assessment.get("analyst_bottom_line"),
                "executive_brief": assessment.get("executive_brief"),
                "scenario_tree": assessment.get("scenario_tree"),
                "ripple_effects": assessment.get("ripple_effects"),
                "source_verification": assessment.get("verification"),
                "status": "active",
            }

            response = (
                supabase.table("ews_verified_alerts")
                .insert(payload)
                .execute()
            )

            if response.data:
                verified_alert_id = response.data[0]["id"]

        except Exception as e:
            assessment["supabase_save_error"] = str(e)

    return {
        "status": "success",
        "architecture": "Agentic Mesh Phase 2",
        "agent": "Gemini Pro Analyst + Red Team",
        "sifted_signal_id": request.sifted_signal_id,
        "verified_alert_id": verified_alert_id,
        "assessment": assessment,
    }
