from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from app.services.conflict_scoring import calculate_conflict_score
from app.services.conflict_data_sources import fetch_conflict_signals
from app.services.conflict_forecaster import generate_conflict_forecast
from app.services.conflict_judgment import generate_executive_judgment
from app.services.conflict_scenarios import generate_conflict_scenarios
from app.services.conflict_simulation_questions import generate_simulation_questions
from app.services.conflict_judgment import generate_executive_judgment
from app.services.conflict_scenarios import generate_conflict_scenarios
from app.services.conflict_simulation_questions import generate_simulation_questions

router = APIRouter(prefix="/api/conflict", tags=["Conflict Forecasting"])

class ConflictForecastRequest(BaseModel):
    country: str
    region: Optional[str] = None
    indicator: Optional[str] = None
    timeframe: Optional[str] = "30d"
    limit: Optional[int] = 10



def get_conflict_graph_context(
    country: str = None,
    region: str = None,
    indicator: str = None
):
    """
    Pull relevant Global Strategic Knowledge Graph context for Conflict Forecasting.
    Safe helper: never crashes the Conflict Forecasting endpoint.
    """
    try:
        from routers.strategic_knowledge_graph import (
            fetch_entity_by_name,
            fetch_relationships_for_entity,
            get_connected_entities,
            build_risk_pathways,
            recommend_modules,
        )

        graph_inputs = [country, indicator, region]
        graph_context = []

        for item in graph_inputs:
            if not item:
                continue

            matched = fetch_entity_by_name(item)
            if not matched:
                continue

            relationships = fetch_relationships_for_entity(matched["id"])
            connected = get_connected_entities(relationships)
            pathways = build_risk_pathways(matched, connected)
            modules = recommend_modules(matched, connected)

            graph_context.append({
                "input": item,
                "matched_entity": matched,
                "connected_entities": connected[:10],
                "risk_pathways": pathways[:8],
                "recommended_modules": modules,
            })

        strategic_pathways = []
        for block in graph_context:
            strategic_pathways.extend(block.get("risk_pathways", []))

        strategic_pathways = sorted(
            strategic_pathways,
            key=lambda x: x.get("risk_score", 0),
            reverse=True
        )[:12]

        return {
            "status": "success",
            "graph_context_available": True,
            "entities_analyzed": len(graph_context),
            "graph_context": graph_context,
            "strategic_pathways": strategic_pathways,
        }

    except Exception as e:
        return {
            "status": "error",
            "graph_context_available": False,
            "error": str(e),
            "graph_context": [],
            "strategic_pathways": [],
        }


@router.get("/health")
def conflict_health():
    return {
        "status": "ok",
        "module": "conflict_forecasting",
        "message": "Conflict Forecasting Command is active"
    }

@router.get("/indicators")
def conflict_indicators():
    try:
        graph_context = get_conflict_graph_context(
            country=request.country,
            region=request.region,
            indicator=request.indicator,
        )
    except Exception as graph_error:
        graph_context = {
            "status": "error",
            "graph_context_available": False,
            "error": str(graph_error),
            "graph_context": [],
            "strategic_pathways": [],
        }

    return {
        "status": "success",
        "strategic_knowledge_graph": graph_context,
        "indicators": [
            "Armed clashes",
            "Troop mobilization",
            "Border incidents",
            "Civil unrest",
            "Election violence",
            "Militia activity",
            "Terrorism activity",
            "Political assassination",
            "Elite fragmentation",
            "Sanctions pressure",
            "Refugee flows",
            "Food and fuel shocks",
            "Cyber operations",
            "Disinformation campaigns",
            "Maritime incidents"
        ]
    }

@router.post("/run-forecast")
def run_conflict_forecast(request: ConflictForecastRequest):

    data_package = fetch_conflict_signals(
        country=request.country,
        indicator=request.indicator,
        limit=request.limit
    )

    sample_signals = data_package["signals"]
    scoring = calculate_conflict_score(sample_signals)
    forecast = generate_conflict_forecast(scoring, sample_signals, request.timeframe)
    executive_judgment = generate_executive_judgment(request.country, scoring, forecast)
    scenarios = generate_conflict_scenarios(request.country, scoring, forecast)
    simulation_questions = generate_simulation_questions(request.country, scoring, forecast)
    executive_judgment = generate_executive_judgment(request.country, scoring, forecast)
    scenarios = generate_conflict_scenarios(request.country, scoring, forecast)
    simulation_questions = generate_simulation_questions(request.country, scoring, forecast)

    return {
        "status": "success",
        "module": "conflict_forecasting",
        "country": request.country,
        "region": request.region,
        "indicator": request.indicator,
        "timeframe": request.timeframe,

        "risk_score": scoring["risk_score"],
        "risk_level": scoring["risk_level"],
        "risk_drivers": scoring.get("risk_drivers", []),
        "signals_used": sample_signals,
        "data_source": data_package,

        "forecast": forecast,

        "executive_judgment": executive_judgment,

        "key_drivers": scoring.get("risk_drivers", [])[:5],

        "scenarios": scenarios,

        "simulation_questions": simulation_questions
    }
