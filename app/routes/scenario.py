from fastapi import APIRouter
from app.schemas.scenario_schema import ScenarioRequest, FollowUpScenarioRequest
from app.services.scenario_engine import (
    run_scenario_simulation,
    run_follow_up_simulation,
    generate_default_questions,
)

router = APIRouter(prefix="/api/scenario", tags=["Scenario Simulation Lab"])


@router.get("/health")
async def scenario_health():
    return {
        "status": "online",
        "module": "scenario_simulation_lab",
        "description": "Adaptive cross-module scenario simulation engine"
    }


@router.get("/templates")
async def scenario_templates():
    return {
        "status": "success",
        "templates": {
            "conflict_forecasting": [
                "Simulate escalation pathway",
                "Simulate cyber-military convergence",
                "Simulate gray-zone crisis",
                "Simulate worst-case conflict trigger"
            ],
            "strategic_early_warning": [
                "Simulate warning-to-crisis transition",
                "Simulate indicator threshold breach",
                "Simulate watchlist deterioration",
                "Simulate daily monitoring priorities"
            ],
            "supply_chain": [
                "Simulate chokepoint disruption",
                "Simulate commodity shock",
                "Simulate shipping reroute",
                "Simulate downstream production impact"
            ],
            "financial_risk": [
                "Simulate market shock",
                "Simulate capital flight",
                "Simulate FX and commodity exposure",
                "Simulate investor risk pathway"
            ],
            "energy_risk": [
                "Simulate oil and gas disruption",
                "Simulate energy price shock",
                "Simulate maritime energy chokepoint crisis",
                "Simulate strategic reserve response"
            ],
            "country_intelligence": [
                "Simulate regime stability risk",
                "Simulate domestic unrest",
                "Simulate policy shift",
                "Simulate alliance realignment"
            ],
            "corporate_exposure": [
                "Simulate supplier disruption",
                "Simulate sanctions exposure",
                "Simulate asset risk",
                "Simulate business continuity stress test"
            ]
        }
    }


@router.post("/run")
async def run_scenario(request: ScenarioRequest):
    payload = request.model_dump()
    result = await run_scenario_simulation(payload)

    return {
        "status": "success",
        "module": "scenario_simulation_lab",
        "input": payload,
        "result": result
    }


@router.post("/follow-up")
async def follow_up_scenario(request: FollowUpScenarioRequest):
    result = await run_follow_up_simulation(
        original_context=request.original_context,
        selected_question=request.selected_question,
        time_horizon=request.time_horizon,
    )

    return {
        "status": "success",
        "module": "scenario_simulation_lab",
        "selected_question": request.selected_question,
        "result": result
    }


@router.post("/questions")
async def scenario_questions(request: ScenarioRequest):
    payload = request.model_dump()
    source_module = payload.get("source_module", "manual")

    questions = generate_default_questions(source_module, payload)

    return {
        "status": "success",
        "module": "scenario_simulation_lab",
        "source_module": source_module,
        "questions": questions
    }
