from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from openai import OpenAI
import os
import json
from supabase import create_client

app = FastAPI(
    title="Sovereign Intelligence API",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all (we tighten later)
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class State(TypedDict, total=False):
    query: str
    geo: str
    energy: str
    security: str
    score: str
    final: str

def geo(state: State) -> State:
    r = client.responses.create(
        model="gpt-4.1-mini",
        input=f"""
You are a geopolitical risk analyst.

Task: Analyze ONLY the geopolitical and political dimensions of this query.
Focus only on:
- government stability
- elections and political legitimacy
- civil-military relations
- foreign relations and diplomatic tensions
- sanctions or external pressure

Do NOT discuss energy or terrorism unless directly relevant to political stability.
Keep it concise.
Output format:
1. Headline
2. Three bullet points
3. One-sentence outlook

Query: {state['query']}
"""
    )
    return {"geo": r.output_text}

def energy(state: State) -> State:
    r = client.responses.create(
        model="gpt-4.1-mini",
        input=f"""
You are an energy risk analyst.

Task: Analyze ONLY the energy risk dimensions of this query.
Focus only on:
- supply shortages
- fuel import dependence
- LNG/oil/gas exposure
- grid reliability
- infrastructure vulnerability
- energy price and fiscal pressure

Do NOT discuss general politics or militancy unless directly relevant to energy security.
Keep it concise.
Output format:
1. Headline
2. Three bullet points
3. One-sentence outlook

Query: {state['query']}
"""
    )
    return {"energy": r.output_text}

def security(state: State) -> State:
    r = client.responses.create(
        model="gpt-4.1-mini",
        input=f"""
You are a security risk analyst.

Task: Analyze ONLY the security dimensions of this query.
Focus only on:
- militancy and terrorism
- insurgency and separatism
- border tensions
- urban unrest
- infrastructure attack risk
- internal security capacity

Do NOT discuss general politics or energy unless directly relevant to security risk.
Keep it concise.
Output format:
1. Headline
2. Three bullet points
3. One-sentence outlook

Query: {state['query']}
"""
    )
    return {"security": r.output_text}

def score(state: State) -> State:
    combined = f"""
GEOPOLITICAL ANALYSIS
{state.get('geo', '')}

ENERGY ANALYSIS
{state.get('energy', '')}

SECURITY ANALYSIS
{state.get('security', '')}
"""
    r = client.responses.create(
        model="gpt-4.1-mini",
        input=f"""
Based only on the analyses below, produce a clean JSON object.

Return ONLY valid JSON.
No markdown. No explanation outside JSON.

Required format:
{{
  "political_score": <number 0-100>,
  "security_score": <number 0-100>,
  "energy_score": <number 0-100>,
  "overall_score": <number 0-100>,
  "summary": "<one short sentence>"
}}

Analyses:
{combined}
"""
    )
    return {"score": r.output_text}

def final(state: State) -> State:
    r = client.responses.create(
        model="gpt-4.1-mini",
        input=f"""
Create a short executive intelligence briefing.

Use:
Geopolitical:
{state.get('geo', '')}

Energy:
{state.get('energy', '')}

Security:
{state.get('security', '')}

Scores:
{state.get('score', '')}

Rules:
- Keep it short
- Avoid repetition
- Output exactly this structure:

Headline:
<one sentence>

Key Judgments:
- <bullet 1>
- <bullet 2>
- <bullet 3>

Outlook:
<one sentence>

Priority Risk:
<one sentence>
"""
    )
    return {"final": r.output_text}

builder = StateGraph(State)

builder.add_node("geo", geo)
builder.add_node("energy", energy)
builder.add_node("security", security)
builder.add_node("score", score)
builder.add_node("final", final)

builder.add_edge(START, "geo")
builder.add_edge(START, "energy")
builder.add_edge(START, "security")

builder.add_edge("geo", "score")
builder.add_edge("energy", "score")
builder.add_edge("security", "score")

builder.add_edge("score", "final")
builder.add_edge("final", END)

graph = builder.compile()

@app.get("/")
def home():
    return {"message": "Sovereign Intelligence API is running"}

@app.post("/analyze")
def analyze(data: dict):
    try:
        result = graph.invoke({"query": data["query"]})

        score_raw = result.get("score", "{}")
        try:
            score_json = json.loads(score_raw)
        except Exception:
            score_json = {
                "political_score": None,
                "security_score": None,
                "energy_score": None,
                "overall_score": None,
                "summary": score_raw
            }

        overall = score_json.get("overall_score")

        if overall is not None:
            if overall >= 80:
                score_json["risk_level"] = "HIGH"
            elif overall >= 60:
                score_json["risk_level"] = "MEDIUM"
            else:
                score_json["risk_level"] = "LOW"

        supabase.table("analysis_results").insert({
            "query": data["query"],
            "country": data.get("country", "Unknown"),
            "result": result.get("final"),
            "geo": result.get("geo"),
            "energy": result.get("energy"),
            "security": result.get("security"),
            "score": json.dumps(scores),
            "political_score": scores["political_score"],
            "security_score": scores["security_score"],
            "economic_score": scores["economic_score"],
            "energy_score": scores["energy_score"],
            "social_score": scores["social_score"],
            "external_score": scores["external_score"],
            "overall_score": scores["overall_score"],
            "risk_level": scores["risk_level"],
            "score_summary": scores["score_summary"]
        }).execute()

        return {
            "query": data["query"],
            "country": data.get("country", "Unknown"),
            "geopolitical": result.get("geo"),
            "energy": result.get("energy"),
            "security": result.get("security"),
            "score": scores,
            "final": result.get("final")
        }

    except Exception as e:
        return {"error": str(e)}

def compute_scores(data: dict) -> dict:
    political = 72
    security = 78
    economic = 64
    energy = 68
    social = 61
    external = 74

    overall = (
        political * 0.20 +
        security * 0.25 +
        economic * 0.15 +
        energy * 0.10 +
        social * 0.15 +
        external * 0.15
    )

    if overall >= 75:
        level = "High"
    elif overall >= 50:
        level = "Moderate"
    else:
        level = "Low"

    return {
        "political_score": political,
        "security_score": security,
        "economic_score": economic,
        "energy_score": energy,
        "social_score": social,
        "external_score": external,
        "overall_score": round(overall, 1),
        "risk_level": level,
        "score_summary": f"Overall geopolitical risk level is {level}."
    }
