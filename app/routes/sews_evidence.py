from __future__ import annotations

import os
from functools import lru_cache
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client, create_client

from app.schemas.sews_evidence import (
    EvidenceIngestRequest,
    EvidenceIngestResponse,
    EvidenceNormalizeRequest,
    EvidenceObjectResponse,
    IndicatorStateRecalculateRequest,
    IndicatorStateResponse,
    ObservationCreateRequest,
    ObservationResponse,
    WarningProblemStateResponse,
)
from app.services.sews_evidence_service import (
    SEWSEvidenceError,
    SEWSEvidenceService,
)
from app.services.sews_indicator_state_service import (
    SEWSIndicatorStateError,
    SEWSIndicatorStateService,
)
from app.services.sews_observation_service import (
    SEWSObservationError,
    SEWSObservationService,
)


router = APIRouter(prefix="/api/sews", tags=["SEWS Evidence"])


@lru_cache(maxsize=1)
def get_sews_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    # Backend must use the service-role key because RLS intentionally blocks
    # client writes to analytical tables.
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured."
        )
    return create_client(url, key)


DB = Annotated[Client, Depends(get_sews_supabase_client)]


def _raise_service_error(exc: Exception) -> None:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=str(exc),
    ) from exc


@router.post(
    "/evidence/ingest",
    response_model=EvidenceIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_evidence(payload: EvidenceIngestRequest, db: DB):
    try:
        return SEWSEvidenceService(db).ingest(payload)
    except SEWSEvidenceError as exc:
        _raise_service_error(exc)


@router.post(
    "/evidence/normalize",
    response_model=EvidenceObjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def normalize_evidence(payload: EvidenceNormalizeRequest, db: DB):
    try:
        return SEWSEvidenceService(db).normalize(payload)
    except SEWSEvidenceError as exc:
        _raise_service_error(exc)


@router.get("/evidence")
def list_evidence(
    db: DB,
    source_key: str | None = None,
    country_iso3: str | None = Query(default=None, min_length=3, max_length=3),
    evidence_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    data = SEWSEvidenceService(db).list_evidence(
        source_key=source_key,
        country_iso3=country_iso3,
        status=evidence_status,
        limit=limit,
    )
    return {"status": "success", "count": len(data), "data": data}


@router.post(
    "/observations",
    response_model=ObservationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_observation(payload: ObservationCreateRequest, db: DB):
    try:
        return SEWSObservationService(db).create(payload)
    except SEWSObservationError as exc:
        _raise_service_error(exc)


@router.get("/observations")
def list_observations(
    db: DB,
    indicator_key: str | None = None,
    warning_problem_key: str | None = None,
    country_iso3: str | None = Query(default=None, min_length=3, max_length=3),
    observation_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    data = SEWSObservationService(db).list_observations(
        indicator_key=indicator_key,
        warning_problem_key=warning_problem_key,
        country_iso3=country_iso3,
        status=observation_status,
        limit=limit,
    )
    return {"status": "success", "count": len(data), "data": data}


@router.post(
    "/indicator-state/recalculate",
    response_model=IndicatorStateResponse,
)
def recalculate_indicator_state(
    payload: IndicatorStateRecalculateRequest,
    db: DB,
):
    try:
        return SEWSIndicatorStateService(db).recalculate(payload)
    except SEWSIndicatorStateError as exc:
        _raise_service_error(exc)


@router.get("/indicator-state/{indicator_key}")
def get_indicator_state(
    indicator_key: str,
    db: DB,
    warning_problem_key: str | None = None,
    country_iso3: str | None = Query(default=None, min_length=3, max_length=3),
    region_key: str | None = None,
) -> dict[str, Any]:
    state_row = SEWSIndicatorStateService(db).get_state(
        indicator_key,
        warning_problem_key=warning_problem_key,
        country_iso3=country_iso3,
        region_key=region_key,
    )
    if not state_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No state found for indicator {indicator_key}.",
        )
    return {"status": "success", "data": state_row}


@router.get(
    "/warning-problems/{warning_problem_key}/state",
    response_model=WarningProblemStateResponse,
)
def get_warning_problem_state(warning_problem_key: str, db: DB):
    return SEWSIndicatorStateService(db).warning_problem_state(
        warning_problem_key
    )
