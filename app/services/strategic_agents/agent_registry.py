from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class AgentDefinition:
    agent_key: str
    name: str
    description: str
    domain: str
    icon: str
    freshness_threshold_minutes: int
    default_schedule_minutes: int
    monitored_topics: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["monitored_topics"] = list(self.monitored_topics)
        return data


AGENT_REGISTRY: dict[str, AgentDefinition] = {
    "conflict_monitoring": AgentDefinition(
        agent_key="conflict_monitoring",
        name="Conflict Monitoring Agent",
        description="Monitors armed conflict, protests, military activity, and escalation risk.",
        domain="conflict",
        icon="crosshair",
        freshness_threshold_minutes=180,
        default_schedule_minutes=60,
        monitored_topics=(
            "Armed Conflict",
            "Military Activity",
            "Protests",
            "Political Violence",
        ),
    ),
    "political_stability": AgentDefinition(
        agent_key="political_stability",
        name="Political Stability Agent",
        description="Assesses elections, institutional stress, governance shocks, and regime stability.",
        domain="political",
        icon="shield",
        freshness_threshold_minutes=360,
        default_schedule_minutes=180,
        monitored_topics=(
            "Elections",
            "Coups",
            "Government Collapse",
            "Institutions",
        ),
    ),
    "economic_risk": AgentDefinition(
        agent_key="economic_risk",
        name="Economic Risk Agent",
        description="Synthesizes macroeconomic stress, inflation, debt, unemployment, currency, and central-bank signals.",
        domain="economic",
        icon="trending-up",
        freshness_threshold_minutes=360,
        default_schedule_minutes=180,
        monitored_topics=(
            "Inflation",
            "Debt",
            "Unemployment",
            "Currency Stress",
        ),
    ),
    "energy_security": AgentDefinition(
        agent_key="energy_security",
        name="Energy Security Agent",
        description="Monitors energy infrastructure, oil and gas disruptions, and supply security.",
        domain="energy",
        icon="fuel",
        freshness_threshold_minutes=180,
        default_schedule_minutes=60,
        monitored_topics=(
            "Oil Supply",
            "Gas Disruption",
            "Nuclear",
            "Pipelines",
        ),
    ),
    "trade_sanctions": AgentDefinition(
        agent_key="trade_sanctions",
        name="Trade & Sanctions Agent",
        description="Monitors sanctions, trade controls, shipping disruptions, and commercial coercion.",
        domain="trade",
        icon="package",
        freshness_threshold_minutes=180,
        default_schedule_minutes=60,
        monitored_topics=(
            "Sanctions",
            "Export Controls",
            "Shipping",
            "Trade Wars",
        ),
    ),
    "executive_briefing": AgentDefinition(
        agent_key="executive_briefing",
        name="Executive Intelligence Briefing",
        description="Synthesizes all domain-agent outputs into a strategic executive briefing.",
        domain="cross_domain",
        icon="star",
        freshness_threshold_minutes=720,
        default_schedule_minutes=360,
        monitored_topics=(
            "Cross-Domain",
            "Strategic Risk",
            "Global Outlook",
        ),
    ),
}


def list_agent_definitions() -> list[dict[str, Any]]:
    return [definition.to_dict() for definition in AGENT_REGISTRY.values()]


def get_agent_definition(agent_key: str) -> AgentDefinition:
    definition = AGENT_REGISTRY.get(agent_key)

    if definition is None:
        raise KeyError(f"Unknown strategic agent: {agent_key}")

    return definition
