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

    prompt  = f"""
    You are a senior geopolitical intelligence analyst producing elite strategic intelligence briefs for Sovereign Intelligence.

    Your writing style must resemble:
    - classified intelligence assessments
    - national security strategic memoranda
    - geopolitical decision-support briefings
    - fusion intelligence products

    CRITICAL STYLE RULES:
    - concise
    - analytical
    - operational
    - serious
    - forward-looking
    - minimal headings
    - no academic structure
    - no repetitive markdown
    - no generic AI phrasing
    - avoid excessive bullet nesting
    - avoid giant section trees

    The report should read like an elite intelligence product, not a verbose AI report.

    OUTPUT STRUCTURE:

    # Executive Judgment

    Short strategic assessment of the situation.

    # Core Assessment

    Integrated geopolitical, economic, military, cyber, and energy assessment.

    # Strategic Analytical Judgment

    Provide expert-level interpretation:
    - escalation logic
    - strategic intent
    - coercive signaling
    - second-order effects
    - alliance dynamics
    - systemic risks

    This section should sound like a senior SME assessment.

    # Most Likely Trajectory

    Concise forward-looking pathway.

    # Most Dangerous Trajectory

    Worst realistic escalation pathway.

    # Key Indicators to Monitor

    Only the most operationally relevant indicators.

    # Intelligence Gaps

    Briefly identify uncertainties or missing visibility.

    # Recommended Actions

    Professional strategic recommendations.

    # Source Notes

    Include subtle source references.

    Generate a complete strategic simulation using:

    Country: {payload.country}
    Trigger: {payload.trigger}
    Warning Level: {payload.warning_level}
    Warning Score: {payload.warning_score}

    Do not ask questions.
    Generate the full intelligence brief immediately.
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
