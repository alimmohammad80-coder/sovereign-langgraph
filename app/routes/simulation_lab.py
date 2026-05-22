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




def get_simulation_graph_context(
    country: str = None,
    region: str = None,
    topic: str = None,
    scenario: str = None
):
    """
    Pull relevant Global Strategic Knowledge Graph context for Scenario Simulation Lab.
    Safe helper: never crashes simulation generation.
    """
    try:
        from routers.strategic_knowledge_graph import (
            fetch_entity_by_name,
            fetch_relationships_for_entity,
            get_connected_entities,
            build_risk_pathways,
            recommend_modules,
        )

        graph_inputs = [country, topic, region, scenario]
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

        scenario_prompts = []
        for pathway in strategic_pathways[:8]:
            source = pathway.get("source_entity")
            target = pathway.get("target_entity")
            relationship = pathway.get("relationship")
            scenario_prompts.append({
                "title": f"{source} → {target} escalation pathway",
                "prompt": (
                    f"Simulate how {source} could affect {target} through the "
                    f"{relationship} pathway. Assess likely-case, worst-case, "
                    f"early indicators, second-order effects, and decision options."
                ),
                "risk_score": pathway.get("risk_score", 50),
                "confidence_score": pathway.get("confidence_score", 70),
            })

        return {
            "status": "success",
            "graph_context_available": True,
            "entities_analyzed": len(graph_context),
            "graph_context": graph_context,
            "strategic_pathways": strategic_pathways,
            "graph_generated_scenarios": scenario_prompts,
        }

    except Exception as e:
        return {
            "status": "error",
            "graph_context_available": False,
            "error": str(e),
            "graph_context": [],
            "strategic_pathways": [],
            "graph_generated_scenarios": [],
        }


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

    try:
        graph_context = get_simulation_graph_context(
            country=getattr(payload, "country", None),
            region=getattr(payload, "region", None),
            topic=getattr(payload, "trigger", None),
            scenario=getattr(payload, "trigger", None),
        )
    except Exception as graph_error:
        graph_context = {
            "status": "error",
            "graph_context_available": False,
            "error": str(graph_error),
            "graph_context": [],
            "strategic_pathways": [],
            "graph_generated_scenarios": [],
        }

    return {
        "status": "success",
        "strategic_knowledge_graph": graph_context,
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
