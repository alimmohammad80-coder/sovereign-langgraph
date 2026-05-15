from fastapi import APIRouter
from pydantic import BaseModel
from openai import OpenAI
from app.services.supabase_service import supabase
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

router = APIRouter(
    prefix="/api/simulation",
    tags=["Simulation Lab"]
)


class SimulationRequest(BaseModel):
    country: str = "China"
    trigger: str
    warning_level: str = "Elevated"
    warning_score: int = 0


@router.post("/from-warning")
def run_simulation(payload: SimulationRequest):

    prompt = f"""
You are Sovereign Intelligence's Simulation Lab.

Run a geopolitical decision-support simulation.

Country/Region: {payload.country}
Warning Level: {payload.warning_level}
Warning Score: {payload.warning_score}
Simulation Trigger: {payload.trigger}

Return a professional scenario simulation with:

1. Baseline situation
2. Trigger event
3. Most likely scenario
4. Most dangerous scenario
5. Cascading geopolitical effects
6. Economic and energy effects
7. Security/military effects
8. Early warning indicators to monitor
9. Decision options
10. Recommended actions

The simulation should be highly strategic, realistic, and professional.
"""

    response = client.chat.completions.create(
        model="gpt-5.5",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a geopolitical simulation and strategic "
                    "forecasting engine for Sovereign Intelligence."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    simulation_text = response.choices[0].message.content

    saved = (
        supabase
        .table("simulation_runs")
        .insert({
            "country": payload.country,
            "trigger": payload.trigger,
            "warning_level": payload.warning_level,
            "warning_score": payload.warning_score,
            "simulation": simulation_text,
            "model": "gpt-5.5"
        })
        .execute()
    )

    return {
        "status": "success",
        "engine": "sovereign_simulation_lab",
        "country": payload.country,
        "trigger": payload.trigger,
        "simulation": simulation_text,
        "saved_run": saved.data
    }


@router.get("/recent")
def recent_simulations(limit: int = 10):

    result = (
        supabase
        .table("simulation_runs")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return {
        "status": "success",
        "count": len(result.data),
        "simulations": result.data
    }
