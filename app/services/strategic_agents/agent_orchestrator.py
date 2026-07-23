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
from app.services.siam.evidence import REPPEvidencePipeline
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

    @staticmethod
    def _regional_signal_identity(
        signal: Any,
    ) -> str:
        return str(
            getattr(signal, "evidence_url", None)
            or getattr(signal, "headline", None)
            or getattr(signal, "signal_id", "")
        ).strip().lower()

    async def _run_regional_agent(
        self,
        *,
        agent: BaseStrategicAgent,
        context: dict[str, Any],
    ):
        """
        Collect country evidence across a region, then perform one
        sector-level regional assessment.

        Existing country collectors remain unchanged.
        """
        region = str(
            context.get("region") or ""
        ).strip()

        countries = context.get(
            "regional_countries"
        ) or []

        if not region or not countries:
            return await agent.run(context=context)

        per_country_limit = max(
            2,
            int(
                context.get(
                    "regional_country_signal_limit",
                    6,
                )
            ),
        )

        regional_limit = max(
            10,
            int(
                context.get(
                    "regional_signal_limit",
                    60,
                )
            ),
        )

        collected = []

        for country in countries:
            country_context = {
                **context,
                "country_iso3": country.get(
                    "country_iso3"
                ),
                "country_name": country.get(
                    "country_name"
                ),
                "region": region,
                "signals": [],
                "signal_limit": per_country_limit,
            }

            try:
                country_signals = (
                    await agent.collect_signals(
                        country_context
                    )
                )
                collected.extend(
                    country_signals
                )
            except Exception as exc:
                print(
                    "[StrategicAgentOrchestrator] "
                    "Regional country collection failed:",
                    agent.agent_key,
                    country.get("country_iso3"),
                    type(exc).__name__,
                    str(exc),
                )

        processed_signals = REPPEvidencePipeline.run(
            collected,
            {
                **context,
                "region": region,
                "regional_country_signal_limit": (
                    per_country_limit
                ),
                "regional_signal_limit": regional_limit,
            },
        )

        regional_context = {
            **context,
            "country_iso3": None,
            "country_name": None,
            "region": region,
        }

        assessment = await agent.analyze(
            processed_signals,
            regional_context,
        )

        # The authoritative assessment is regional even though the
        # underlying evidence retains country attribution.
        assessment.country_iso3 = None
        assessment.country_name = None
        assessment.region = region

        metadata = agent.build_freshness_metadata(
            signals=processed_signals,
            assessment=assessment,
            context=regional_context,
        )

        assessment.assessment_generated_at = (
            assessment.generated_at
        )
        assessment.latest_evidence_at = metadata[
            "latest_evidence_at"
        ]
        assessment.oldest_material_evidence_at = metadata[
            "oldest_material_evidence_at"
        ]
        assessment.freshness_status = metadata[
            "freshness_status"
        ]
        assessment.evidence_composition = metadata[
            "evidence_composition"
        ]
        assessment.source_freshness = metadata[
            "source_freshness"
        ]

        return assessment

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

            assessment = await self._run_regional_agent(
                agent=agent,
                context=safe_context,
            )
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
