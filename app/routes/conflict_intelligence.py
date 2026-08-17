from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.services.conflict_intelligence.ontology_service import OntologyService

router = APIRouter(prefix="/api/conflict-intelligence", tags=["Conflict Intelligence"])


def service() -> OntologyService:
    return OntologyService()


@router.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "success",
        "data": {
            "service": "conflict-intelligence",
            "version": "phase1-foundation-v1",
            "deterministic": True,
            "ai_scoring_enabled": False,
        },
    }


@router.get("/summary")
def summary() -> dict[str, Any]:
    try:
        return {"status": "success", "data": service().summary()}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _list(
    entity: str,
    *,
    region: str | None = None,
    subregion: str | None = None,
    active: bool | None = True,
    review_status: str | None = None,
    status: str | None = None,
    disputed: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    filters = {
        "region": region,
        "subregion": subregion,
        "active": active,
        "review_status": review_status,
        "status": status,
        "disputed_flag": disputed,
    }
    filters = {k: v for k, v in filters.items() if v is not None}
    try:
        data = service().list_entity(entity, filters=filters, limit=limit, offset=offset)
        return {"status": "success", "data": data}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/countries")
def countries(
    region: str | None = None,
    subregion: str | None = None,
    active: bool | None = True,
    review_status: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return _list(
        "countries",
        region=region,
        subregion=subregion,
        active=active,
        review_status=review_status,
        limit=limit,
        offset=offset,
    )


@router.get("/dyads")
def dyads(
    disputed: bool | None = None,
    active: bool | None = True,
    review_status: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return _list(
        "dyads",
        disputed=disputed,
        active=active,
        review_status=review_status,
        limit=limit,
        offset=offset,
    )


@router.get("/territories")
def territories(
    status: str | None = None,
    active: bool | None = True,
    review_status: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return _list(
        "territories",
        status=status,
        active=active,
        review_status=review_status,
        limit=limit,
        offset=offset,
    )


@router.get("/frozen-conflicts")
def frozen_conflicts(
    active: bool | None = True,
    review_status: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return _list(
        "frozen_conflicts",
        active=active,
        review_status=review_status,
        limit=limit,
        offset=offset,
    )


@router.get("/actors")
def actors(
    active: bool | None = True,
    review_status: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return _list(
        "actors",
        active=active,
        review_status=review_status,
        limit=limit,
        offset=offset,
    )


@router.get("/episodes")
def episodes(
    status: str | None = None,
    review_status: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return _list(
        "episodes",
        status=status,
        active=None,
        review_status=review_status,
        limit=limit,
        offset=offset,
    )


@router.get("/disputes")
def disputes(
    status: str | None = None,
    active: bool | None = True,
    review_status: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return _list(
        "disputes",
        status=status,
        active=active,
        review_status=review_status,
        limit=limit,
        offset=offset,
    )


@router.get("/non-state-organizations")
def non_state_organizations(
    active: bool | None = True,
    review_status: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return _list(
        "non_state_organizations",
        active=active,
        review_status=review_status,
        limit=limit,
        offset=offset,
    )


@router.get("/governing-authorities")
def governing_authorities(
    active: bool | None = True,
    review_status: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return _list(
        "governing_authorities",
        active=active,
        review_status=review_status,
        limit=limit,
        offset=offset,
    )


@router.get("/historical-episodes")
def historical_episodes(
    active: bool | None = True,
    review_status: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return _list(
        "historical_episodes",
        active=active,
        review_status=review_status,
        limit=limit,
        offset=offset,
    )




@router.get("/country-aliases")
def country_aliases(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return _list(
        "country_aliases",
        limit=limit,
        offset=offset,
    )


@router.get("/observations")
def observations(
    active: bool | None = True,
    review_status: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return _list(
        "observations",
        active=active,
        review_status=review_status,
        limit=limit,
        offset=offset,
    )


from app.schemas.conflict_intelligence.observations import (
    ConflictObservationCreate,
)
from app.services.conflict_intelligence.observation_ingestion_service import (
    ConflictObservationIngestionService,
)


@router.post("/observations")
def create_observation(
    payload: ConflictObservationCreate,
):
    try:
        result = (
            ConflictObservationIngestionService()
            .ingest(
                payload.model_dump()
            )
        )

        return {
            "status": "success",
            "data": result,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


from app.services.conflict_intelligence.conflict_state_engine import (
    ConflictStateEngine,
)


@router.post("/state/{conflict_id}/assess")
def assess_conflict_state(
    conflict_id: int,
    window_days: int = Query(
        30,
        ge=1,
        le=365,
    ),
):
    try:
        result = (
            ConflictStateEngine()
            .assess(
                conflict_id,
                window_days,
            )
        )

        return {
            "status": "success",
            "data": result,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc


@router.get("/states")
def conflict_states(
    limit: int = Query(
        50,
        ge=1,
        le=500,
    ),
    offset: int = Query(
        0,
        ge=0,
    ),
):
    return _list(
        "current_states",
        limit=limit,
        offset=offset,
    )


@router.get("/state-history")
def conflict_state_history(
    conflict_id: int | None = None,
    limit: int = Query(
        100,
        ge=1,
        le=1000,
    ),
    offset: int = Query(
        0,
        ge=0,
    ),
):
    try:
        from app.repositories.conflict_intelligence_repository import (
            get_supabase_client,
        )

        db = get_supabase_client()

        query = (
            db.table("conflict_state_history")
            .select("*", count="exact")
        )

        if conflict_id is not None:
            query = query.eq(
                "conflict_id",
                conflict_id,
            )

        result = (
            query
            .order(
                "calculated_at",
                desc=True,
            )
            .range(
                offset,
                offset + limit - 1,
            )
            .execute()
        )

        return {
            "status": "success",
            "data": {
                "items": result.data or [],
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "count": result.count or 0,
                },
            },
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        ) from exc

@router.get("/state-timeline")
def state_timeline(
    conflict_id: int | None = None,
    limit: int = Query(
        1000,
        ge=1,
        le=5000,
    ),
    offset: int = Query(
        0,
        ge=0,
    ),
):
    try:
        from app.repositories.conflict_intelligence_repository import (
            get_supabase_client,
        )

        db = get_supabase_client()

        query = (
            db.table(
                "conflict_state_timeline"
            )
            .select(
                "*",
                count="exact",
            )
        )

        if conflict_id is not None:
            query = query.eq(
                "conflict_id",
                conflict_id,
            )

        result = (
            query
            .order(
                "year",
                desc=False,
            )
            .range(
                offset,
                offset + limit - 1,
            )
            .execute()
        )

        return {
            "status": "success",
            "data": {
                "items": result.data or [],
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "count": result.count or 0,
                },
            },
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        ) from exc


@router.get("/transition-matrix")
def transition_matrix(
    from_state: str | None = None,
    limit: int = Query(
        100,
        ge=1,
        le=500,
    ),
):
    try:
        from app.repositories.conflict_intelligence_repository import (
            get_supabase_client,
        )

        db = get_supabase_client()

        query = (
            db.table(
                "conflict_state_transitions"
            )
            .select("*")
            .eq(
                "active",
                True,
            )
        )

        if from_state:
            query = query.eq(
                "from_state",
                from_state,
            )

        rows = (
            query
            .order(
                "from_state"
            )
            .order(
                "probability",
                desc=True,
            )
            .limit(limit)
            .execute()
            .data
            or []
        )

        return {
            "status": "success",
            "data": {
                "items": rows,
                "count": len(rows),
            },
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        ) from exc
