from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from app.agents.base_agent import AgentAssessment
from app.intelligence.storage import get_supabase_client


DEGRADED_FRESHNESS_STATUSES = {
    "data_degraded",
    "degraded",
    "collection_failed",
    "failed",
    "insufficient",
    "insufficient_evidence",
    "no_current_evidence",
    "unavailable",
}

DEGRADED_ANALYTICAL_STATUSES = {
    "degraded",
    "insufficient",
    "insufficient_evidence",
    "collection_failed",
    "failed",
    "unavailable",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _client():
    client = get_supabase_client()

    if client is None:
        raise RuntimeError("Supabase client is not configured.")

    return client


def _normalized(value: Any) -> str:
    return str(value or "").strip().lower()


def _registry_freshness_status(
    assessment: AgentAssessment,
    *,
    promotable: bool,
) -> str:
    if not promotable:
        return "stale"

    freshness = _normalized(
        assessment.freshness_status
    )

    if freshness in {
        "current",
        "fresh",
    }:
        return "current"

    if freshness in {
        "stale",
        "aging",
    }:
        return "stale"

    return "unknown"


def evaluate_assessment_persistence(
    assessment: AgentAssessment,
) -> dict[str, Any]:
    """
    Determine whether an assessment may become the latest authoritative
    strategic-agent output.

    Every execution remains in strategic_agent_runs. Only sufficiently
    supported assessments are inserted into strategic_agent_outputs.
    """

    freshness_status = _normalized(
        assessment.freshness_status
    )
    analytical_status = _normalized(
        assessment.analytical_status
    )

    drivers = assessment.key_drivers or []
    indicators = assessment.indicators or []
    evidence = assessment.evidence_composition or {}
    related_signal_ids = assessment.related_signal_ids or []

    risk_score = float(assessment.risk_score or 0)
    confidence = float(assessment.confidence or 0)

    evidence_count = 0

    for value in evidence.values():
        try:
            evidence_count += int(value or 0)
        except (TypeError, ValueError):
            continue

    structurally_insufficient = (
        risk_score == 0
        and confidence <= 30
        and not drivers
        and not indicators
    )

    no_supporting_evidence = (
        evidence_count == 0
        and not related_signal_ids
        and not drivers
        and not indicators
    )

    if freshness_status in DEGRADED_FRESHNESS_STATUSES:
        return {
            "promotable": False,
            "quality_status": "degraded",
            "reason": (
                f"degraded_freshness_status:"
                f"{freshness_status}"
            ),
        }

    if analytical_status in DEGRADED_ANALYTICAL_STATUSES:
        return {
            "promotable": False,
            "quality_status": "degraded",
            "reason": (
                f"degraded_analytical_status:"
                f"{analytical_status}"
            ),
        }

    if structurally_insufficient:
        return {
            "promotable": False,
            "quality_status": "insufficient",
            "reason": "insufficient_assessment_output",
        }

    if no_supporting_evidence:
        return {
            "promotable": False,
            "quality_status": "insufficient",
            "reason": "no_supporting_evidence",
        }

    return {
        "promotable": True,
        "quality_status": "authoritative",
        "reason": "assessment_quality_sufficient",
    }


def create_agent_run(
    *,
    run_id: str,
    agent_key: str,
    trigger_type: str,
    started_at: str,
    scoring_version: str,
    input_signal_count: int = 0,
    country_iso3: str | None = None,
    country_name: str | None = None,
    region: str | None = None,
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
            "country_iso3": (
                country_iso3.strip().upper()
                if country_iso3
                else None
            ),
            "country_name": country_name,
            "region": region,
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
) -> dict[str, Any]:
    """
    Complete an execution and conditionally promote its assessment.

    strategic_agent_runs:
        Append-only execution/audit history.

    strategic_agent_outputs:
        Valid, promotable assessments used as authoritative latest state.
    """

    client = _client()
    assessment_data = asdict(assessment)

    persistence_decision = (
        evaluate_assessment_persistence(assessment)
    )

    client.table("strategic_agent_runs").update(
        {
            "status": "completed",
            "completed_at": completed_at,
            "input_signal_count": input_signal_count,
            "output_signal_count": len(
                assessment.related_signal_ids
            ),
            "risk_score": assessment.risk_score,
            "confidence": assessment.confidence,
            "model_provider": model_provider,
            "model_name": model_name,
        }
    ).eq("id", run_id).execute()

    if not persistence_decision["promotable"]:
        client.table("strategic_agent_runs").update(
            {
                "assessment_promoted": False,
                "quality_status": persistence_decision[
                    "quality_status"
                ],
                "persistence_reason": persistence_decision[
                    "reason"
                ],
                "preserved_previous_assessment": True,
            }
        ).eq("id", run_id).execute()

        # Record the degraded execution operationally, but do not change
        # the registry fields representing the latest valid assessment.
        client.table("strategic_agent_registry").update(
            {
                "operational_status": "degraded",
                "last_completed_at": completed_at,
                "updated_at": completed_at,
            }
        ).eq(
            "agent_key",
            assessment.agent_key,
        ).execute()

        print(
            "[StrategicAgentPersistence] "
            "Run retained for audit; assessment not promoted:",
            assessment.agent_key,
            run_id,
            persistence_decision["reason"],
        )

        return {
            "run_persisted": True,
            "output_persisted": False,
            "assessment_promoted": False,
            "quality_status": persistence_decision[
                "quality_status"
            ],
            "persistence_reason": persistence_decision[
                "reason"
            ],
            "preserved_previous_assessment": True,
        }

    client.table("strategic_agent_runs").update(
        {
            "assessment_promoted": True,
            "quality_status": persistence_decision[
                "quality_status"
            ],
            "persistence_reason": persistence_decision[
                "reason"
            ],
            "preserved_previous_assessment": False,
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
            "executive_summary": (
                assessment.executive_summary
            ),
            "risk_score": assessment.risk_score,
            "risk_level": assessment.risk_level,
            "confidence": assessment.confidence,
            "key_drivers": assessment.key_drivers,
            "indicators": assessment.indicators,
            "forecast_probabilities": (
                assessment.forecast_probabilities
            ),
            "implications": assessment.implications,
            "recommendations": assessment.recommendations,
            "intelligence_gaps": (
                assessment.intelligence_gaps
            ),
            "related_signal_ids": (
                assessment.related_signal_ids
            ),
            "presentation_payload": assessment_data,
            "valid_from": assessment.generated_at,
            "created_at": completed_at,
        }
    ).execute()

    client.table("strategic_agent_registry").update(
        {
            "operational_status": "healthy",
            "analytical_status": (
                assessment.analytical_status
            ),
            "latest_run_id": run_id,
            "last_completed_at": completed_at,
            "latest_signal_count": len(
                assessment.related_signal_ids
            ),
            "latest_risk_score": assessment.risk_score,
            "latest_confidence": assessment.confidence,
            "updated_at": completed_at,
        }
    ).eq(
        "agent_key",
        assessment.agent_key,
    ).execute()

    return {
        "run_persisted": True,
        "output_persisted": True,
        "assessment_promoted": True,
        "quality_status": persistence_decision[
            "quality_status"
        ],
        "persistence_reason": persistence_decision[
            "reason"
        ],
        "preserved_previous_assessment": False,
    }


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
            "error_code": (
                "strategic_agent_execution_failed"
            ),
            "error_message": error_message,
        }
    ).eq("id", run_id).execute()
