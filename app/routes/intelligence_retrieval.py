import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from supabase import create_client
from openai import OpenAI

router = APIRouter(prefix="/api", tags=["intelligence-retrieval"])

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)



class AnalystEntry(BaseModel):
    module: str
    country: Optional[str] = None
    region: Optional[str] = None
    sector: Optional[str] = None
    indicator: Optional[str] = None
    title: str
    event_summary: Optional[str] = None
    analyst_assessment: str
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    source_date: Optional[str] = None
    confidence_level: Optional[str] = None
    severity: Optional[str] = None
    reliability: Optional[str] = None
    tags: Optional[List[str]] = []


class RunWithKnowledgeRequest(BaseModel):
    module: str
    country: Optional[str] = None
    region: Optional[str] = None
    sector: Optional[str] = None
    indicator: Optional[str] = None
    query: Optional[str] = None
    tags: Optional[List[str]] = []


@router.post("/intel/analyst-entry")
def create_analyst_entry(payload: AnalystEntry):
    try:
        result = supabase.table("analyst_intelligence_entries").insert(payload.dict()).execute()
        return {"status": "success", "data": result.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/intel/search")
def search_intel(
    module: Optional[str] = None,
    country: Optional[str] = None,
    sector: Optional[str] = None,
    indicator: Optional[str] = None,
    limit: int = 10
):
    try:
        q = supabase.table("analyst_intelligence_entries").select("*")

        if module:
            q = q.eq("module", module)
        if country:
            q = q.eq("country", country)
        if sector:
            q = q.eq("sector", sector)
        if indicator:
            q = q.eq("indicator", indicator)

        result = q.order("created_at", desc=True).limit(limit).execute()
        return {"status": "success", "count": len(result.data), "data": result.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reports/run-with-knowledge")
def run_with_knowledge(payload: RunWithKnowledgeRequest):
    try:
        entries_q = supabase.table("analyst_intelligence_entries").select("*")
        news_q = supabase.table("news_signals").select("*")
        profiles_q = supabase.table("country_sector_profiles").select("*")
        chunks_q = supabase.table("document_chunks").select("*")

        for q in [entries_q, news_q, chunks_q]:
            pass

        if payload.module:
            entries_q = entries_q.eq("module", payload.module)
            news_q = news_q.eq("module", payload.module)
            chunks_q = chunks_q.eq("module", payload.module)

        if payload.country:
            entries_q = entries_q.eq("country", payload.country)
            news_q = news_q.eq("country", payload.country)
            profiles_q = profiles_q.eq("country", payload.country)
            chunks_q = chunks_q.eq("country", payload.country)

        if payload.sector:
            entries_q = entries_q.eq("sector", payload.sector)
            news_q = news_q.eq("sector", payload.sector)
            profiles_q = profiles_q.eq("sector", payload.sector)
            chunks_q = chunks_q.eq("sector", payload.sector)

        if payload.indicator:
            entries_q = entries_q.eq("indicator", payload.indicator)
            news_q = news_q.eq("indicator", payload.indicator)
            chunks_q = chunks_q.eq("indicator", payload.indicator)

        entries = entries_q.order("created_at", desc=True).limit(8).execute().data
        news = news_q.order("created_at", desc=True).limit(8).execute().data
        profiles = profiles_q.limit(3).execute().data
        chunks = chunks_q.limit(8).execute().data

        evidence_packet = {
            "analyst_entries": entries,
            "news_signals": news,
            "country_sector_profiles": profiles,
            "document_chunks": chunks,
        }

        prompt = f"""
You are Sovereign Intelligence AI, an intelligence analysis system.

Use the retrieved internal evidence below to produce a professional intelligence report.

User query:
{payload.query}

Module:
{payload.module}

Country:
{payload.country}

Sector:
{payload.sector}

Indicator:
{payload.indicator}

Retrieved Evidence:
{json.dumps(evidence_packet, indent=2, default=str)}

Write the report in JSON only with these fields:
- bluf
- current_situation
- strategic_assessment
- forecast_outlook
- operational_implications
- confidence_level
- risk_score
- risk_level
- evidence_used

Rules:
- Start with a clear BLUF.
- Use the internal analyst evidence where available.
- Do not invent sources.
- If evidence is limited, explain the limitation.
- Make it sound like an intelligence early warning report.
"""

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You produce structured strategic intelligence reports using only provided evidence."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
        )

        raw_output = completion.choices[0].message.content

        try:
            report = json.loads(raw_output)
        except Exception:
            report = {
                "bluf": raw_output,
                "current_situation": "",
                "strategic_assessment": "",
                "forecast_outlook": "",
                "operational_implications": "",
                "confidence_level": "Medium",
                "risk_score": None,
                "risk_level": "Unknown",
                "evidence_used": evidence_packet,
            }

        supabase.table("report_runs").insert({
            "module": payload.module,
            "country": payload.country,
            "region": payload.region,
            "sector": payload.sector,
            "indicator": payload.indicator,
            "query": payload.query,
            "bluf": report["bluf"],
            "current_situation": report["current_situation"],
            "strategic_assessment": report["strategic_assessment"],
            "forecast_outlook": report["forecast_outlook"],
            "operational_implications": report["operational_implications"],
            "full_report": report,
            "model_used": "gpt-4o-mini",
            "confidence_level": report.get("confidence_level"),
            "risk_score": report.get("risk_score"),
            "risk_level": report.get("risk_level")
        }).execute()

        return {"status": "success", "report": report}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
