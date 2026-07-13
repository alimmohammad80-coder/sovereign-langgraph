from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.agents.base_agent import BaseStrategicAgent
from app.agents.conflict_monitoring_agent import ConflictMonitoringAgent
from app.agents.political_stability_agent import PoliticalStabilityAgent
from app.agents.economic_risk_agent import EconomicRiskAgent
from app.agents.energy_security_agent import EnergySecurityAgent
from app.agents.trade_sanctions_agent import TradeSanctionsAgent
from app.agents.executive_briefing_agent import ExecutiveBriefingAgent
from app.services.strategic_agents.nemotron_client import NEMOTRON_MODEL
from app.services.strategic_agents.persistence import (
    complete_agent_run,
    create_agent_run,
    fail_agent_run,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class StrategicAgentOrchestrator:
    def __init__(self) -> None:
        self._agents: dict[str, BaseStrategicAgent] = {
            "conflict_monitoring": ConflictMonitoringAgent(),
            "political_stability": PoliticalStabilityAgent(),
            "economic_risk": EconomicRiskAgent(),
            "energy_security": EnergySecurityAgent(),
            "trade_sanctions": TradeSanctionsAgent(),
            "executive_briefing": ExecutiveBriefingAgent(),
        }

    def available_agent_keys(self) -> list[str]:
        return list(self._agents.keys())

    def get_agent(self, agent_key: str) -> BaseStrategicAgent:
        agent = self._agents.get(agent_key)

        if agent is None:
            raise KeyError(
                f"Agent '{agent_key}' is registered but is not yet implemented."
            )

        return agent

    async def run_agent(
        self,
        agent_key: str,
        context: dict[str, Any] | None = None,
        trigger_type: str = "manual",
    ) -> dict[str, Any]:
        run_id = str(uuid4())
        started_at = utc_now_iso()
        safe_context = context or {}

        try:
            agent = self.get_agent(agent_key)

            create_agent_run(
                run_id=run_id,
                agent_key=agent_key,
                trigger_type=trigger_type,
                started_at=started_at,
                scoring_version=agent.scoring_version,
                input_signal_count=len(
                    safe_context.get("signals", [])
                ),
                country_iso3=safe_context.get(
                    "country_iso3"
                ),
                country_name=safe_context.get(
                    "country_name"
                ),
                region=safe_context.get("region"),
            )

            assessment = await agent.run(context=safe_context)
            completed_at = utc_now_iso()

            persistence = complete_agent_run(
                run_id=run_id,
                assessment=assessment,
                completed_at=completed_at,
                input_signal_count=len(assessment.related_signal_ids),
                model_provider="nvidia",
                model_name=NEMOTRON_MODEL,
            )

            return {
                "status": "success",
                "run": {
                    "id": run_id,
                    "agent_key": agent_key,
                    "run_status": "completed",
                    "trigger_type": trigger_type,
                    "started_at": started_at,
                    "completed_at": completed_at,
                    "scoring_version": agent.scoring_version,
                    "persisted": persistence.get(
                        "run_persisted",
                        False,
                    ),
                    "output_persisted": persistence.get(
                        "output_persisted",
                        False,
                    ),
                    "assessment_promoted": persistence.get(
                        "assessment_promoted",
                        False,
                    ),
                    "quality_status": persistence.get(
                        "quality_status",
                    ),
                    "persistence_reason": persistence.get(
                        "persistence_reason",
                    ),
                    "preserved_previous_assessment": (
                        persistence.get(
                            "preserved_previous_assessment",
                            False,
                        )
                    ),
                },
                "assessment": asdict(assessment),
            }

        except Exception as exc:
            completed_at = utc_now_iso()

            print(
                "[StrategicAgentOrchestrator] Run failed:",
                agent_key,
                run_id,
                type(exc).__name__,
                str(exc),
            )

            try:
                fail_agent_run(
                    run_id=run_id,
                    error_message=str(exc),
                    completed_at=completed_at,
                )
            except Exception:
                pass

            return {
                "status": "error",
                "run": {
                    "id": run_id,
                    "agent_key": agent_key,
                    "run_status": "failed",
                    "trigger_type": trigger_type,
                    "started_at": started_at,
                    "completed_at": completed_at,
                    "persisted": False,
                },
                "error": {
                    "code": "strategic_agent_execution_failed",
                    "message": str(exc),
                },
            }


strategic_agent_orchestrator = StrategicAgentOrchestrator()
