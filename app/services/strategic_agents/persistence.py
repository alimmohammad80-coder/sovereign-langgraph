from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from app.agents.base_agent import AgentAssessment
from app.intelligence.storage import get_supabase_client


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _client():
    client = get_supabase_client()

    if client is None:
        raise RuntimeError("Supabase client is not configured.")

    return client


def create_agent_run(
    *,
    run_id: str,
    agent_key: str,
    trigger_type: str,
    started_at: str,
    scoring_version: str,
    input_signal_count: int = 0,
) -> None:
    _client().table("strategic_agent_runs").insert(
        {
            "id": run_id,
            "agent_key": agent_key,
            "status": "analyzing",
            "trigger_type": trigger_type,
            "started_at": started_at,
            "input_signal_count": input_signal_count,
            "scoring_version": scoring_version,
            "created_at": started_at,
        }
    ).execute()


def complete_agent_run(
    *,
    run_id: str,
    assessment: AgentAssessment,
    completed_at: str,
    input_signal_count: int,
    model_provider: str | None = None,
    model_name: str | None = None,
) -> None:
    client = _client()
    assessment_data = asdict(assessment)

    client.table("strategic_agent_runs").update(
        {
            "status": "completed",
            "completed_at": completed_at,
            "input_signal_count": input_signal_count,
            "output_signal_count": len(assessment.related_signal_ids),
            "risk_score": assessment.risk_score,
            "confidence": assessment.confidence,
            "model_provider": model_provider,
            "model_name": model_name,
        }
    ).eq("id", run_id).execute()

    client.table("strategic_agent_outputs").insert(
        {
            "run_id": run_id,
            "agent_key": assessment.agent_key,
            "output_type": "assessment",
            "title": assessment.title,
            "country_iso3": assessment.country_iso3,
            "country_name": assessment.country_name,
            "region": assessment.region,
            "bluf": assessment.bluf,
            "executive_summary": assessment.executive_summary,
            "risk_score": assessment.risk_score,
            "risk_level": assessment.risk_level,
            "confidence": assessment.confidence,
            "key_drivers": assessment.key_drivers,
            "indicators": assessment.indicators,
            "forecast_probabilities": assessment.forecast_probabilities,
            "implications": assessment.implications,
            "recommendations": assessment.recommendations,
            "intelligence_gaps": assessment.intelligence_gaps,
            "related_signal_ids": assessment.related_signal_ids,
            "presentation_payload": assessment_data,
            "valid_from": assessment.generated_at,
            "created_at": completed_at,
        }
    ).execute()

    client.table("strategic_agent_registry").update(
        {
            "operational_status": "healthy",
            "analytical_status": assessment.analytical_status,
            "freshness_status": "current",
            "latest_run_id": run_id,
            "last_completed_at": completed_at,
            "latest_signal_count": len(assessment.related_signal_ids),
            "latest_risk_score": assessment.risk_score,
            "latest_confidence": assessment.confidence,
            "updated_at": completed_at,
        }
    ).eq("agent_key", assessment.agent_key).execute()


def fail_agent_run(
    *,
    run_id: str,
    error_message: str,
    completed_at: str | None = None,
) -> None:
    finished_at = completed_at or utc_now_iso()

    _client().table("strategic_agent_runs").update(
        {
            "status": "failed",
            "completed_at": finished_at,
            "error_code": "strategic_agent_execution_failed",
            "error_message": error_message,
        }
    ).eq("id", run_id).execute()
