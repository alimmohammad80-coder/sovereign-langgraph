from typing import Any, Dict, List


def _safe_value(report: Dict[str, Any], keys: List[str], default: str) -> str:
    for key in keys:
        value = report.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return default


def generate_simulation_questions(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate strategic, open-ended simulation questions from any Sovereign Intelligence
    agentic analysis report.

    These questions are designed to move the user from:
    analysis -> uncertainty -> scenario simulation -> decision support.
    """

    country = _safe_value(
        report,
        ["country", "selected_country", "country_name", "region"],
        "the affected country or region",
    )

    agent = _safe_value(
        report,
        ["agent", "module", "analysis_type", "topic"],
        "the current intelligence assessment",
    )

    risk_level = _safe_value(
        report,
        ["risk_level", "threat_level", "warning_level"],
        "the current risk level",
    )

    executive_judgment = _safe_value(
        report,
        ["executive_judgment", "summary", "assessment", "analytic_judgment"],
        "the current intelligence signals",
    )

    return [
        {
            "id": "sim_escalation_pathway",
            "title": "Escalation Pathway",
            "category": "Geopolitical / Security",
            "question": (
                f"What if the current risk indicators in {country} escalate over the next "
                f"30 to 90 days? What political, security, economic, energy, and diplomatic "
                f"consequences could follow?"
            ),
            "why_it_matters": (
                "This simulation helps users examine how today’s signals could evolve into "
                "a wider strategic crisis."
            ),
        },
        {
            "id": "sim_second_order_effects",
            "title": "Second-Order Effects",
            "category": "Strategic Foresight",
            "question": (
                f"What second-order effects could emerge from this {agent} assessment if "
                f"the underlying drivers continue or worsen in {country}?"
            ),
            "why_it_matters": (
                "This helps identify indirect consequences that may not be immediately visible "
                "in the original report."
            ),
        },
        {
            "id": "sim_worst_case",
            "title": "Most Dangerous Plausible Scenario",
            "category": "Risk Escalation",
            "question": (
                f"What is the most dangerous plausible scenario for {country} if the current "
                f"risk level remains {risk_level} or deteriorates further?"
            ),
            "why_it_matters": (
                "This supports red-team thinking by stress-testing the most severe but realistic "
                "outcome."
            ),
        },
        {
            "id": "sim_market_supply_chain",
            "title": "Market and Supply Chain Shock",
            "category": "Economic / Supply Chain",
            "question": (
                f"If instability in {country} intensifies, how could it affect markets, energy "
                f"flows, logistics routes, insurance costs, sanctions exposure, and corporate risk?"
            ),
            "why_it_matters": (
                "This connects geopolitical analysis to business, investor, and operational exposure."
            ),
        },
        {
            "id": "sim_policy_response",
            "title": "Policy and Actor Response",
            "category": "Decision Support",
            "question": (
                f"How might regional actors, major powers, private firms, and international "
                f"institutions respond if the situation in {country} follows the trajectory "
                f"described in this report?"
            ),
            "why_it_matters": (
                "This helps users anticipate how governments, markets, and institutions may react."
            ),
        },
        {
            "id": "sim_strategic_surprise",
            "title": "Strategic Surprise",
            "category": "Warning Intelligence",
            "question": (
                f"What unexpected development could emerge from the current situation in "
                f"{country}, and how would it change the strategic outlook?"
            ),
            "why_it_matters": (
                "This forces the simulation to consider low-probability, high-impact shifts."
            ),
        },
        {
            "id": "sim_report_based",
            "title": "Report-Derived Scenario",
            "category": "Custom Simulation",
            "question": (
                f"Based on this judgment — '{executive_judgment}' — what are the most likely, "
                f"most dangerous, and most surprising scenarios that could emerge next?"
            ),
            "why_it_matters": (
                "This directly converts the agent’s conclusion into a simulation-ready question."
            ),
        },
    ]
