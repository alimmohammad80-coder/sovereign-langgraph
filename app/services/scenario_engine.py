import os
import json
from typing import Any, Dict

from openai import AsyncOpenAI

from app.services.scenario_prompt import SYSTEM_PROMPT, OUTPUT_CONTRACT


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_SCENARIO_MODEL", "gpt-5.5")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)


def build_adaptive_user_prompt(payload: Dict[str, Any]) -> str:
    source_module = payload.get("source_module", "manual")
    scenario_type = payload.get("scenario_type", "adaptive")

    return f"""
Generate an adaptive Sovereign Intelligence scenario simulation.

Source module:
{source_module}

Scenario type:
{scenario_type}

Input intelligence package:
{json.dumps(payload, indent=2, ensure_ascii=False)}

Instructions:
1. Adapt the simulation to the source module.
2. Generate cross-module collision effects.
3. Generate scenario questions that can be sent back into this Scenario Lab.
4. Build best-case, most-likely, and worst-case pathways.
5. Include escalation ladder.
6. Include decision options.
7. Include monitoring indicators with watch thresholds.
8. Include collection priorities.
9. Clearly separate evidence, inference, and uncertainty.

{OUTPUT_CONTRACT}
"""


async def run_scenario_simulation(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not OPENAI_API_KEY:
        return fallback_scenario(payload, reason="OPENAI_API_KEY is missing")

    user_prompt = build_adaptive_user_prompt(payload)

    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.25,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        return json.loads(content)

    except Exception as exc:
        return fallback_scenario(payload, reason=str(exc))


async def run_follow_up_simulation(original_context: Dict[str, Any], selected_question: str, time_horizon: str = "30 days") -> Dict[str, Any]:
    merged_payload = dict(original_context)
    merged_payload["user_question"] = selected_question
    merged_payload["time_horizon"] = time_horizon
    merged_payload["scenario_type"] = "follow_up"
    merged_payload["event"] = merged_payload.get("event") or selected_question

    return await run_scenario_simulation(merged_payload)


def generate_default_questions(source_module: str, payload: Dict[str, Any]) -> list:
    country = payload.get("country") or payload.get("entity") or "the target country"
    sector = payload.get("sector") or "critical sectors"
    event = payload.get("event") or "the current risk environment"

    common = [
        {
            "question": f"What happens if {event} escalates over the next 30 days?",
            "scenario_type": "escalation_pathway",
            "best_for_module": "all",
            "why_this_matters": "Tests near-term deterioration and decision thresholds."
        },
        {
            "question": f"What is the worst-case scenario for {country}?",
            "scenario_type": "worst_case",
            "best_for_module": "all",
            "why_this_matters": "Identifies severe but plausible downside risk."
        }
    ]

    module_specific = {
        "conflict_forecasting": [
            {
                "question": f"What military or gray-zone trigger could push {country} into crisis?",
                "scenario_type": "conflict_escalation",
                "best_for_module": "conflict_forecasting",
                "why_this_matters": "Identifies conflict thresholds and warning signs."
            },
            {
                "question": f"What happens if cyber activity converges with military pressure in {country}?",
                "scenario_type": "cyber_military_convergence",
                "best_for_module": "conflict_forecasting",
                "why_this_matters": "Tests combined escalation pathways."
            }
        ],
        "strategic_early_warning": [
            {
                "question": f"Which indicators would confirm that {country} is moving from warning to crisis?",
                "scenario_type": "indicator_threshold",
                "best_for_module": "strategic_early_warning",
                "why_this_matters": "Clarifies watch conditions and collection priorities."
            },
            {
                "question": f"What early warning signals should be monitored daily for {country}?",
                "scenario_type": "daily_watch",
                "best_for_module": "strategic_early_warning",
                "why_this_matters": "Improves operational monitoring."
            }
        ],
        "supply_chain": [
            {
                "question": f"What happens if {sector} supply chains are disrupted for 30 days?",
                "scenario_type": "supply_chain_disruption",
                "best_for_module": "supply_chain",
                "why_this_matters": "Tests operational resilience and downstream effects."
            },
            {
                "question": f"What chokepoint failure would create the largest cascading impact for {sector}?",
                "scenario_type": "chokepoint_failure",
                "best_for_module": "supply_chain",
                "why_this_matters": "Identifies the most dangerous logistics bottleneck."
            }
        ],
        "financial_risk": [
            {
                "question": f"What market shock could follow from escalation in {country}?",
                "scenario_type": "market_shock",
                "best_for_module": "financial_risk",
                "why_this_matters": "Links geopolitical risk to investor exposure."
            },
            {
                "question": f"What happens to FX, commodities, and capital flows if {event} worsens?",
                "scenario_type": "macro_financial_stress",
                "best_for_module": "financial_risk",
                "why_this_matters": "Tests financial contagion channels."
            }
        ],
        "energy_risk": [
            {
                "question": f"What happens if energy flows linked to {country} are disrupted?",
                "scenario_type": "energy_disruption",
                "best_for_module": "energy_risk",
                "why_this_matters": "Tests price shock and energy security exposure."
            }
        ],
        "corporate_exposure": [
            {
                "question": f"Which corporate assets, suppliers, or operations are most exposed if {event} escalates?",
                "scenario_type": "corporate_exposure",
                "best_for_module": "corporate_exposure",
                "why_this_matters": "Connects strategic risk to business continuity."
            }
        ],
        "country_intelligence": [
            {
                "question": f"What domestic political instability pathway is most plausible in {country}?",
                "scenario_type": "political_stability",
                "best_for_module": "country_intelligence",
                "why_this_matters": "Tests regime, governance, and internal security risk."
            }
        ],
    }

    return common + module_specific.get(source_module, [])


def fallback_scenario(payload: Dict[str, Any], reason: str = "Unknown error") -> Dict[str, Any]:
    source_module = payload.get("source_module", "manual")
    event = payload.get("event", "Scenario event")
    country = payload.get("country") or payload.get("entity") or "Target"
    risk_score = payload.get("risk_score") or 50
    risk_level = payload.get("risk_level") or "Watch"
    time_horizon = payload.get("time_horizon") or "30 days"

    return {
        "scenario_title": f"{country} Scenario Simulation",
        "source_module": source_module,
        "scenario_type": payload.get("scenario_type", "adaptive"),
        "executive_judgment": f"{event} requires structured scenario monitoring. GPT generation fallback was used because: {reason}",
        "baseline_assessment": {
            "current_state": event,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "time_horizon": time_horizon,
            "confidence": 45,
            "key_assumptions": [
                "Input data may be incomplete.",
                "Scenario assessment should be updated with live signals."
            ],
            "known_unknowns": [
                "Intent of key actors",
                "Trigger timing",
                "Operational thresholds"
            ]
        },
        "cross_module_collision": {
            "conflict_implications": ["Potential escalation if coercive activity increases."],
            "early_warning_implications": ["Monitor indicator movement and threshold crossings."],
            "supply_chain_implications": ["Potential disruption to exposed sectors and logistics routes."],
            "financial_implications": ["Risk premium may rise if escalation becomes visible."],
            "energy_implications": ["Energy exposure depends on geography, chokepoints, and commodity linkages."],
            "corporate_exposure_implications": ["Companies with local assets or suppliers may face elevated risk."],
            "country_risk_implications": ["Political, economic, and security stress could compound."]
        },
        "scenarios": {
            "best_case": {
                "summary": "Risk remains contained and does not cross into crisis.",
                "probability": 25,
                "pathway": ["Signals stabilize", "Actors avoid major escalation", "Markets absorb uncertainty"],
                "triggers_that_support_this_case": ["De-escalatory statements", "Reduced incident frequency"],
                "impact": "Moderate",
                "decision_relevance": "Continue monitoring without activating crisis posture."
            },
            "most_likely": {
                "summary": "Pressure remains elevated with periodic escalation signals.",
                "probability": 55,
                "pathway": ["Signals remain active", "Risk premium rises", "Decision-makers increase monitoring"],
                "triggers_that_support_this_case": ["Sustained activity", "Mixed official messaging", "No decisive de-escalation"],
                "impact": "High",
                "decision_relevance": "Prepare contingency plans and monitor thresholds."
            },
            "worst_case": {
                "summary": "A trigger event causes rapid escalation and cascading effects.",
                "probability": 20,
                "pathway": ["Incident occurs", "Response cycle accelerates", "Markets and exposed sectors react"],
                "triggers_that_support_this_case": ["Military incident", "Major cyber event", "Sanctions escalation"],
                "impact": "Severe",
                "decision_relevance": "Activate crisis management and exposure reduction."
            }
        },
        "escalation_ladder": [
            {
                "stage": "Watch",
                "description": "Elevated but contained risk.",
                "indicators": ["Rising rhetoric", "Increased monitoring signals"],
                "estimated_probability": 45
            },
            {
                "stage": "Warning",
                "description": "Multiple indicators converge.",
                "indicators": ["Operational movement", "Cyber activity", "Policy warnings"],
                "estimated_probability": 35
            },
            {
                "stage": "Crisis",
                "description": "Trigger event causes rapid deterioration.",
                "indicators": ["Incident", "Emergency response", "Market shock"],
                "estimated_probability": 20
            }
        ],
        "second_order_effects": [
            "Higher insurance and operating costs",
            "Supply-chain delays",
            "Policy and diplomatic pressure"
        ],
        "third_order_effects": [
            "Longer-term investment shift",
            "Strategic decoupling pressure",
            "Regional security posture changes"
        ],
        "decision_options": [
            {
                "option": "Monitor",
                "description": "Track indicators and update scenario probabilities.",
                "benefit": "Preserves flexibility.",
                "risk": "May underreact if escalation is rapid.",
                "when_to_use": "When signals are active but below crisis threshold."
            },
            {
                "option": "Prepare",
                "description": "Develop contingency plans and exposure maps.",
                "benefit": "Improves response speed.",
                "risk": "Requires resources before crisis confirmation.",
                "when_to_use": "When indicators begin converging."
            },
            {
                "option": "Act",
                "description": "Reduce exposure and activate crisis posture.",
                "benefit": "Limits downside risk.",
                "risk": "May be costly if risk de-escalates.",
                "when_to_use": "When thresholds are crossed."
            }
        ],
        "monitoring_indicators": [
            {
                "indicator": "Escalatory official statements",
                "why_it_matters": "Signals intent and possible policy shift.",
                "watch_threshold": "Multiple senior-level statements within 72 hours.",
                "relevant_modules": ["strategic_early_warning", "country_intelligence"]
            },
            {
                "indicator": "Operational movement or disruption",
                "why_it_matters": "Shows risk moving from rhetoric to action.",
                "watch_threshold": "Confirmed movement, incident, closure, or disruption.",
                "relevant_modules": ["conflict_forecasting", "supply_chain", "energy_risk"]
            }
        ],
        "collection_priorities": [
            "Confirm actor intent",
            "Track operational indicators",
            "Monitor financial and supply-chain spillovers"
        ],
        "simulation_questions": generate_default_questions(source_module, payload),
        "evidence_inference_uncertainty": {
            "evidence": payload.get("drivers", []),
            "inference": ["Scenario pathways are inferred from the provided risk context."],
            "uncertainty": ["Live data depth and actor intent remain uncertain."]
        },
        "confidence_score": 45
    }
