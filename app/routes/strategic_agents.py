from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from app.intelligence.storage import get_supabase_client
from pydantic import BaseModel, Field

from app.services.strategic_agents.agent_orchestrator import (
    strategic_agent_orchestrator,
)
from app.services.strategic_agents.agent_registry import (
    get_agent_definition,
    list_agent_definitions,
)


router = APIRouter(
    prefix="/api/strategic-agents",
    tags=["Strategic Intelligence Agents"],
)


class RunAgentRequest(BaseModel):
    trigger_type: Literal[
        "manual",
        "scheduled",
        "signal",
        "system",
    ] = "manual"

    country_iso3: str | None = None
    region: str | None = None

    signals: list[dict[str, Any]] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)


@router.get("")
async def list_agents() -> dict[str, Any]:
    implemented = set(
        strategic_agent_orchestrator.available_agent_keys()
    )

    agents = []

    for definition in list_agent_definitions():
        agent_key = definition["agent_key"]

        agents.append(
            {
                **definition,
                "implemented": agent_key in implemented,
                "operational_status": "idle",
                "analytical_status": "nominal",
                "freshness_status": "stale",
                "latest_signal_count": 0,
                "active_alert_count": 0,
                "last_completed_at": None,
            }
        )

    return {
        "status": "success",
        "count": len(agents),
        "data": agents,
    }


@router.get("/status")
async def strategic_agent_status() -> dict[str, Any]:
    return {
        "status": "success",
        "system": {
            "operational_status": "healthy",
            "schedule_status": "not_configured",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        },
        "summary": {
            "agents": 6,
            "implemented_agents": len(
                strategic_agent_orchestrator.available_agent_keys()
            ),
            "signals": 0,
            "active_alerts": 0,
            "latest_run_at": None,
        },
    }


@router.get("/scheduler/status")
async def get_scheduler_status() -> dict[str, Any]:
    from app.services.strategic_agents.scheduled_runner import (
        strategic_agent_scheduled_runner,
    )

    return {
        "status": "success",
        "data": strategic_agent_scheduled_runner.status(),
    }


@router.get("/{agent_key}")
async def get_agent(agent_key: str) -> dict[str, Any]:
    try:
        definition = get_agent_definition(agent_key)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    implemented = (
        agent_key
        in strategic_agent_orchestrator.available_agent_keys()
    )

    return {
        "status": "success",
        "data": {
            **definition.to_dict(),
            "implemented": implemented,
            "operational_status": "idle",
            "analytical_status": "nominal",
            "freshness_status": "stale",
        },
    }


@router.post("/{agent_key}/run")
async def run_agent(
    agent_key: str,
    request: RunAgentRequest,
) -> dict[str, Any]:
    try:
        get_agent_definition(agent_key)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    context = {
        **request.context,
        "country_iso3": request.country_iso3,
        "region": request.region,
        "signals": request.signals,
    }

    result = await strategic_agent_orchestrator.run_agent(
        agent_key=agent_key,
        context=context,
        trigger_type=request.trigger_type,
    )

    if result["status"] == "error":
        message = result.get("error", {}).get(
            "message",
            "Strategic agent execution failed.",
        )

        if "not yet implemented" in message:
            raise HTTPException(
                status_code=501,
                detail=message,
            )

        raise HTTPException(
            status_code=500,
            detail=message,
        )

    return result


@router.get("/{agent_key}/latest")
async def get_latest_agent_output(
    agent_key: str,
    country_iso3: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    try:
        get_agent_definition(agent_key)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    client = get_supabase_client()

    if client is None:
        raise HTTPException(
            status_code=503,
            detail="Supabase is not configured.",
        )

    query = (
        client.table("strategic_agent_outputs")
        .select("*")
        .eq("agent_key", agent_key)
    )

    if country_iso3:
        query = query.eq(
            "country_iso3",
            country_iso3.strip().upper(),
        )

    if region:
        query = query.eq(
            "region",
            region.strip(),
        )

    result = (
        query
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not result.data:
        run_query = (
            client.table("strategic_agent_runs")
            .select(
                "id,status,trigger_type,started_at,completed_at,"
                "risk_score,confidence,error_code,error_message,"
                "country_iso3,country_name,region,created_at"
            )
            .eq("agent_key", agent_key)
        )

        if country_iso3:
            run_query = run_query.eq(
                "country_iso3",
                country_iso3.strip().upper(),
            )
        elif region:
            run_query = run_query.eq(
                "region",
                region.strip(),
            )

        latest_run_result = (
            run_query
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        latest_run = (
            dict(latest_run_result.data[0])
            if latest_run_result.data
            else None
        )

        return {
            "status": "success",
            "data": {
                "assessment": None,
                "assessment_status": "unavailable",
                "authoritative_run_id": None,
                "latest_run": latest_run,
                "newer_run_not_promoted": bool(
                    latest_run
                ),
                "preserved_previous_assessment": False,
            },
        }

    output = dict(result.data[0])
    presentation = output.get("presentation_payload") or {}

    for field_name in (
        "assessment_generated_at",
        "latest_evidence_at",
        "oldest_material_evidence_at",
        "freshness_status",
        "evidence_composition",
        "source_freshness",
    ):
        if field_name not in output:
            output[field_name] = presentation.get(
                field_name
            )

    run_query = (
        client.table("strategic_agent_runs")
        .select(
            "id,status,trigger_type,started_at,completed_at,"
            "risk_score,confidence,error_code,error_message,"
            "assessment_promoted,quality_status,persistence_reason,"
            "preserved_previous_assessment,"
            "country_iso3,country_name,region,created_at"
        )
        .eq("agent_key", agent_key)
    )

    if country_iso3:
        run_query = run_query.eq(
            "country_iso3",
            country_iso3.strip().upper(),
        )
    elif region:
        run_query = run_query.eq(
            "region",
            region.strip(),
        )

    latest_run_result = (
        run_query
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    latest_run = (
        dict(latest_run_result.data[0])
        if latest_run_result.data
        else None
    )

    authoritative_run_id = output.get("run_id")

    newer_run_not_promoted = bool(
        latest_run
        and latest_run.get("id")
        != authoritative_run_id
    )

    return {
        "status": "success",
        "data": {
            "assessment": output,
            "assessment_status": "authoritative",
            "authoritative_run_id": (
                authoritative_run_id
            ),
            "latest_run": latest_run,
            "newer_run_not_promoted": (
                newer_run_not_promoted
            ),
            "preserved_previous_assessment": (
                newer_run_not_promoted
            ),
        },
    }


@router.get("/{agent_key}/runs")
async def get_agent_runs(
    agent_key: str,
    limit: int = 20,
) -> dict[str, Any]:
    try:
        get_agent_definition(agent_key)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    safe_limit = max(1, min(limit, 100))
    client = get_supabase_client()

    if client is None:
        raise HTTPException(
            status_code=503,
            detail="Supabase is not configured.",
        )

    result = (
        client.table("strategic_agent_runs")
        .select(
            "id,agent_key,status,trigger_type,started_at,completed_at,"
            "input_signal_count,output_signal_count,risk_score,confidence,"
            "model_provider,model_name,error_code,error_message,created_at"
        )
        .eq("agent_key", agent_key)
        .order("created_at", desc=True)
        .limit(safe_limit)
        .execute()
    )

    return {
        "status": "success",
        "count": len(result.data),
        "data": result.data,
    }


@router.get("/{agent_key}/history")
async def get_agent_output_history(
    agent_key: str,
    limit: int = 20,
) -> dict[str, Any]:
    try:
        get_agent_definition(agent_key)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    safe_limit = max(1, min(limit, 100))
    client = get_supabase_client()

    if client is None:
        raise HTTPException(
            status_code=503,
            detail="Supabase is not configured.",
        )

    result = (
        client.table("strategic_agent_outputs")
        .select(
            "id,run_id,agent_key,title,country_iso3,country_name,region,"
            "bluf,risk_score,risk_level,confidence,"
            "forecast_probabilities,created_at"
        )
        .eq("agent_key", agent_key)
        .order("created_at", desc=True)
        .limit(safe_limit)
        .execute()
    )

    return {
        "status": "success",
        "count": len(result.data),
        "data": result.data,
    }


@router.get("/scheduler/status")
async def get_scheduler_status() -> dict[str, Any]:
    from app.services.strategic_agents.scheduled_runner import (
        strategic_agent_scheduled_runner,
    )

    return {
        "status": "success",
        "data": strategic_agent_scheduled_runner.status(),
    }
