from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

try:
    from app.services.scenario_engine import run_scenario_simulation, generate_default_questions
except Exception:
    run_scenario_simulation = None
    generate_default_questions = None


router = APIRouter(prefix="/api/simulation-lab", tags=["Simulation Lab"])


class SimulationLabRequest(BaseModel):
    title: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    actor: Optional[str] = None
    sector: Optional[str] = None
    scenario: Optional[str] = None
    event: Optional[str] = None
    question: Optional[str] = None
    time_horizon: Optional[str] = "30 days"
    source_module: Optional[str] = "simulation_lab"
    risk_score: Optional[int] = None
    risk_level: Optional[str] = None
    drivers: List[str] = Field(default_factory=list)
    indicators: List[str] = Field(default_factory=list)
    source_report: Dict[str, Any] = Field(default_factory=dict)


@router.get("/health")
async def simulation_lab_health():
    return {
        "status": "online",
        "module": "simulation_lab",
        "message": "Old Simulation Lab route preserved with GPT-5.5 enrichment available"
    }


@router.post("/run")
async def run_simulation_lab(request: SimulationLabRequest):
    payload = request.model_dump()

    event = (
        payload.get("event")
        or payload.get("scenario")
        or payload.get("question")
        or payload.get("title")
        or "Strategic simulation"
    )

    scenario_payload = {
        "source_module": payload.get("source_module") or "simulation_lab",
        "scenario_type": "legacy_simulation_lab_refined",
        "country": payload.get("country"),
        "region": payload.get("region"),
        "sector": payload.get("sector"),
        "entity": payload.get("actor"),
        "event": event,
        "risk_score": payload.get("risk_score"),
        "risk_level": payload.get("risk_level"),
        "time_horizon": payload.get("time_horizon"),
        "drivers": payload.get("drivers", []),
        "indicators": payload.get("indicators", []),
        "source_report": payload.get("source_report", {}),
        "user_question": payload.get("question") or event,
    }

    if run_scenario_simulation:
        enriched = await run_scenario_simulation(scenario_payload)
    else:
        enriched = {
            "scenario_title": event,
            "executive_judgment": "Simulation Lab is online, but GPT enrichment engine is unavailable.",
            "simulation_questions": []
        }

    old_style_response = {
        "title": enriched.get("scenario_title") or event,
        "executive_summary": enriched.get("executive_judgment", ""),
        "baseline": enriched.get("baseline_assessment", {}),
        "best_case": enriched.get("scenarios", {}).get("best_case", {}),
        "most_likely": enriched.get("scenarios", {}).get("most_likely", {}),
        "worst_case": enriched.get("scenarios", {}).get("worst_case", {}),
        "escalation_pathway": enriched.get("escalation_ladder", []),
        "second_order_effects": enriched.get("second_order_effects", []),
        "third_order_effects": enriched.get("third_order_effects", []),
        "decision_options": enriched.get("decision_options", []),
        "monitoring_indicators": enriched.get("monitoring_indicators", []),
        "simulation_questions": enriched.get("simulation_questions", []),
        "confidence_score": enriched.get("confidence_score", 0),
        "raw_enriched_result": enriched
    }

    return {
        "status": "success",
        "module": "simulation_lab",
        "version": "legacy_refined_gpt55",
        "input": payload,
        "result": old_style_response
    }


@router.post("/questions")
async def simulation_lab_questions(request: SimulationLabRequest):
    payload = request.model_dump()
    source_module = payload.get("source_module") or "simulation_lab"

    if generate_default_questions:
        questions = generate_default_questions(source_module, payload)
    else:
        event = payload.get("event") or payload.get("scenario") or "this scenario"
        questions = [
            {
                "question": f"What happens if {event} escalates over the next 30 days?",
                "scenario_type": "escalation",
                "best_for_module": source_module,
                "why_this_matters": "Tests near-term escalation risk."
            },
            {
                "question": f"What is the worst-case pathway for {event}?",
                "scenario_type": "worst_case",
                "best_for_module": source_module,
                "why_this_matters": "Identifies severe downside risk."
            }
        ]

    return {
        "status": "success",
        "module": "simulation_lab",
        "questions": questions
    }
