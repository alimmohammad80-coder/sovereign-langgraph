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


from app.services.conflict_intelligence.conflict_transition_forecaster import (
    ConflictTransitionForecaster,
)


@router.post("/forecast/{conflict_id}")
def forecast_conflict(
    conflict_id: int,
    horizon_days: int = Query(
        30,
        ge=1,
        le=365,
    ),
):
    try:
        result = (
            ConflictTransitionForecaster()
            .forecast(
                conflict_id,
                horizon_days,
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
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        ) from exc


@router.get("/forecast/{conflict_id}/horizons")
def forecast_conflict_horizons(
    conflict_id: int,
):
    try:
        result = (
            ConflictTransitionForecaster()
            .forecast_all_horizons(
                conflict_id
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
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        ) from exc


from app.services.conflict_intelligence.pre_conflict_escalation_model import (
    PreConflictEscalationModel,
)


@router.get("/forecast/{conflict_id}/escalation")
def forecast_conflict_escalation(
    conflict_id: int,
    horizon_days: int = Query(
        30,
        ge=30,
        le=365,
    ),
    lookback_days: int = Query(
        30,
        ge=1,
        le=365,
    ),
):
    try:
        result = (
            PreConflictEscalationModel()
            .forecast(
                conflict_id,
                horizon_days,
                lookback_days,
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
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        ) from exc


from app.services.conflict_intelligence.dyadic_escalation_model import (
    DyadicEscalationModel,
)


@router.get("/forecast/{conflict_id}/dyadic")
def forecast_dyadic_escalation(
    conflict_id: int,
    horizon_days: int = Query(
        30,
        ge=30,
        le=365,
    ),
    lookback_days: int = Query(
        30,
        ge=1,
        le=365,
    ),
):
    try:
        result = (
            DyadicEscalationModel()
            .forecast(
                conflict_id,
                horizon_days,
                lookback_days,
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
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        ) from exc


from app.services.conflict_intelligence.frozen_conflict_hazard_model import (
    FrozenConflictHazardModel,
)


@router.get("/forecast/{conflict_id}/frozen-hazard")
def forecast_frozen_conflict_hazard(
    conflict_id: int,
    horizon_days: int = Query(
        365,
        ge=30,
        le=365,
    ),
    lookback_days: int = Query(
        30,
        ge=1,
        le=365,
    ),
):
    try:
        result = (
            FrozenConflictHazardModel()
            .forecast(
                conflict_id,
                horizon_days,
                lookback_days,
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
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        ) from exc


from app.services.conflict_intelligence.conflict_forecast_ensemble import (
    ConflictForecastEnsemble,
)


@router.get("/forecast/{conflict_id}/ensemble")
def forecast_conflict_ensemble(
    conflict_id: int,
    horizon_days: int = Query(
        30,
        ge=30,
        le=365,
    ),
    lookback_days: int = Query(
        30,
        ge=1,
        le=365,
    ),
):
    try:
        result = (
            ConflictForecastEnsemble()
            .forecast(
                conflict_id,
                horizon_days,
                lookback_days,
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
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        ) from exc


from app.services.conflict_intelligence.conflict_forecast_persistence import (
    ConflictForecastPersistence,
)


@router.post("/forecast/{conflict_id}/run")
def run_conflict_forecast(
    conflict_id: int,
    horizon_days: int = Query(
        30,
        ge=30,
        le=365,
    ),
    lookback_days: int = Query(
        30,
        ge=1,
        le=365,
    ),
):
    try:
        result = (
            ConflictForecastPersistence()
            .run(
                conflict_id,
                horizon_days,
                lookback_days,
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
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        ) from exc


from app.services.conflict_intelligence.conflict_forecast_outcome_resolver import (
    ConflictForecastOutcomeResolver,
)


@router.post("/forecast-outcomes/resolve")
def resolve_conflict_forecast_outcomes(
    limit: int = Query(
        500,
        ge=1,
        le=5000,
    ),
):
    try:
        result = (
            ConflictForecastOutcomeResolver()
            .resolve(
                limit
            )
        )

        return {
            "status": "success",
            "data": result,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        ) from exc


from app.services.conflict_intelligence.conflict_forecast_evaluator import (
    ConflictForecastEvaluator,
)


@router.get("/forecast-performance")
def conflict_forecast_performance(
    threshold: float = Query(
        0.30,
        ge=0.0,
        le=1.0,
    ),
    ensemble_model: str | None = None,
    limit: int = Query(
        10000,
        ge=1,
        le=50000,
    ),
):
    try:
        result = (
            ConflictForecastEvaluator()
            .evaluate(
                threshold=threshold,
                ensemble_model=ensemble_model,
                limit=limit,
            )
        )

        return {
            "status": "success",
            "data": result,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        ) from exc


from app.services.conflict_intelligence.hawkes_escalation_model import (
    HawkesEscalationModel,
)


@router.get("/forecast/{conflict_id}/hawkes")
def forecast_hawkes_escalation(
    conflict_id: int,
    horizon_days: int = Query(
        30,
        ge=30,
        le=365,
    ),
    lookback_days: int = Query(
        90,
        ge=1,
        le=730,
    ),
):
    try:
        result = (
            HawkesEscalationModel()
            .forecast(
                conflict_id,
                horizon_days,
                lookback_days,
            )
        )

        return {
            "status":
                "success",

            "data":
                result,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        ) from exc


from app.services.conflict_intelligence.ripple_propagation_engine import (
    RipplePropagationEngine,
)


@router.post("/ripple/{conflict_id}/run")
def run_conflict_ripple(
    conflict_id: int,
    horizon_days: int = Query(
        30,
        ge=30,
        le=365,
    ),
    lookback_days: int = Query(
        30,
        ge=1,
        le=365,
    ),
    max_depth: int = Query(
        3,
        ge=1,
        le=4,
    ),
):
    try:
        result = (
            RipplePropagationEngine()
            .run(
                conflict_id=conflict_id,
                horizon_days=horizon_days,
                lookback_days=lookback_days,
                max_depth=max_depth,
                persist=True,
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
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        ) from exc


from app.services.conflict_intelligence.analysis_packet_builder import (
    ConflictAnalysisPacketBuilder,
)


@router.get("/analysis-packet/{conflict_id}")
def get_analysis_packet(
    conflict_id: int,
    horizon_days: int = Query(
        365,
        ge=30,
        le=365,
    ),
    lookback_days: int = Query(
        90,
        ge=1,
        le=365,
    ),
    ripple_depth: int = Query(
        3,
        ge=1,
        le=4,
    ),
):
    try:
        packet = (
            ConflictAnalysisPacketBuilder()
            .build(
                conflict_id=conflict_id,
                horizon_days=horizon_days,
                lookback_days=lookback_days,
                ripple_depth=ripple_depth,
            )
        )

        return {
            "status": "success",
            "data": packet,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        ) from exc


from app.services.conflict_intelligence.conflict_news_evidence_bridge import (
    ConflictNewsEvidenceBridge,
)


@router.post("/evidence/ingest-news")
def ingest_conflict_news_evidence(
    limit: int = Query(
        500,
        ge=1,
        le=5000,
    ),
):
    try:
        result = (
            ConflictNewsEvidenceBridge()
            .run(
                limit=limit
            )
        )

        return {
            "status": "success",
            "data": result,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        ) from exc


from app.services.conflict_intelligence.conflict_collection_orchestrator import (
    ConflictCollectionOrchestrator,
)


@router.post("/collection/run")
async def run_conflict_collection(
    query: str = Query(
        ...,
        min_length=2,
        max_length=250,
    ),
    limit_per_source: int = Query(
        25,
        ge=1,
        le=100,
    ),
):
    try:
        result = (
            await ConflictCollectionOrchestrator()
            .run(
                query=query,
                limit_per_source=limit_per_source,
            )
        )

        return {
            "status": "success",
            "data": result,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        ) from exc


from app.services.conflict_intelligence.conflict_intelligence_analyst import (
    ConflictIntelligenceAnalyst,
)


@router.post("/analysis/{conflict_id}")
def run_conflict_intelligence_analysis(
    conflict_id: int,
    horizon_days: int = Query(
        365,
        ge=30,
        le=365,
    ),
    lookback_days: int = Query(
        90,
        ge=1,
        le=365,
    ),
    ripple_depth: int = Query(
        3,
        ge=1,
        le=4,
    ),
    provider: str | None = Query(
        None,
    ),
    model: str | None = Query(
        None,
    ),
):
    try:
        result = (
            ConflictIntelligenceAnalyst()
            .analyze(
                conflict_id=conflict_id,
                horizon_days=horizon_days,
                lookback_days=lookback_days,
                ripple_depth=ripple_depth,
                preferred_provider=provider,
                preferred_model=model,
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
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        ) from exc


from app.services.conflict_intelligence.conflict_evidence_observation_bridge import (
    ConflictEvidenceObservationBridge,
)


@router.post("/evidence/promote-observations")
def promote_conflict_evidence_to_observations(
    conflict_id: int | None = Query(
        None,
    ),
    limit: int = Query(
        500,
        ge=1,
        le=5000,
    ),
    recompute_state: bool = Query(
        True,
    ),
):
    try:
        result = (
            ConflictEvidenceObservationBridge()
            .run(
                conflict_id=conflict_id,
                limit=limit,
                recompute_state=recompute_state,
            )
        )

        return {
            "status": "success",
            "data": result,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        ) from exc


from app.services.conflict_intelligence.conflict_report_persistence import (
    ConflictReportPersistence,
)


@router.get("/analysis/{conflict_id}/latest")
def get_latest_conflict_intelligence_report(
    conflict_id: int,
):
    try:
        report = (
            ConflictReportPersistence()
            .latest(
                conflict_id
            )
        )

        if not report:
            raise HTTPException(
                status_code=404,
                detail=(
                    "No validated conflict intelligence "
                    "report is available."
                ),
            )

        return {
            "status": "success",
            "data": report,
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        ) from exc


@router.get("/analysis/{conflict_id}/history")
def get_conflict_intelligence_report_history(
    conflict_id: int,
    limit: int = Query(
        20,
        ge=1,
        le=100,
    ),
):
    try:
        reports = (
            ConflictReportPersistence()
            .history(
                conflict_id,
                limit=limit,
            )
        )

        return {
            "status": "success",
            "count": len(reports),
            "data": reports,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        ) from exc


# ============================================================
# Async Conflict Executive Analysis Jobs
# ============================================================

from fastapi import BackgroundTasks

from app.services.conflict_intelligence.conflict_analysis_job_service import (
    ConflictAnalysisJobService,
)


@router.post("/analysis-jobs")
def create_conflict_analysis_job(
    background_tasks: BackgroundTasks,
    conflict_id: int = Query(..., ge=1),
    horizon_days: int = Query(
        365,
        ge=30,
        le=365,
    ),
    lookback_days: int = Query(
        90,
        ge=1,
        le=365,
    ),
    ripple_depth: int = Query(
        3,
        ge=1,
        le=4,
    ),
    provider: str | None = Query(
        "NVIDIA",
    ),
    model: str | None = Query(
        "nvidia/nemotron-3-ultra-550b-a55b",
    ),
):
    try:

        service = (
            ConflictAnalysisJobService()
        )

        job = service.create(
            conflict_id=conflict_id,
            horizon_days=horizon_days,
            lookback_days=lookback_days,
            ripple_depth=ripple_depth,
            preferred_provider=provider,
            preferred_model=model,
        )

        background_tasks.add_task(
            service.run,
            str(job["id"]),
        )

        return {
            "status":
                "success",

            "data": {
                "analysis_id":
                    str(job["id"]),

                "conflict_id":
                    conflict_id,

                "status":
                    "queued",
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


@router.get("/analysis-jobs/{analysis_id}")
def get_conflict_analysis_job(
    analysis_id: str,
):
    try:

        job = (
            ConflictAnalysisJobService()
            .get(analysis_id)
        )

        if not job:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Conflict analysis job "
                    "not found."
                ),
            )

        response = {
            "analysis_id":
                str(job["id"]),

            "conflict_id":
                job["conflict_id"],

            "status":
                job["status"],

            "provider":
                job.get("provider"),

            "model":
                job.get("model"),

            "created_at":
                job.get("created_at"),

            "started_at":
                job.get("started_at"),

            "completed_at":
                job.get("completed_at"),
        }

        if job["status"] == "completed":
            response["result"] = (
                job.get("result")
            )

            response["qa"] = (
                job.get("qa")
            )

        elif job["status"] == "failed":
            response["error"] = (
                job.get("error_message")
            )

        return {
            "status":
                "success",

            "data":
                response,
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        ) from exc


# ============================================================
# Canonical Conflict Resolution
# ============================================================

from app.services.conflict_intelligence.canonical_conflict_resolver import (
    CanonicalConflictResolver,
)


@router.get("/resolve")
def resolve_canonical_conflict(
    participant_a: str = Query(
        ...,
        min_length=2,
        max_length=100,
    ),
    participant_b: str = Query(
        ...,
        min_length=2,
        max_length=100,
    ),
    territory: str | None = Query(
        None,
        max_length=200,
    ),
):
    try:
        result = (
            CanonicalConflictResolver()
            .resolve(
                participant_a=
                    participant_a,

                participant_b=
                    participant_b,

                territory=
                    territory,
            )
        )

        return {
            "status":
                "success",

            "data":
                result,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        ) from exc


# ============================================================
# Agent-Orchestrated Conflict Executive Analysis
# ============================================================

from app.schemas.conflict_intelligence.agent_analysis import (
    ConflictAgentAnalysisRequest,
)


@router.post(
    "/agent-analysis-jobs",
    summary="Create conflict executive analysis job",
    description=(
        "Creates an asynchronous Conflict Intelligence Agent job from "
        "selected countries, region, conflict type, indicators, and "
        "forecast horizon. Canonical conflict resolution is optional. "
        "The agent gathers baseline conflict data, current observations, "
        "current evidence/news, and deterministic forecast outputs when "
        "available, then sends the governed packet through the AI gateway."
    ),
)
def create_conflict_agent_analysis_job(
    payload: ConflictAgentAnalysisRequest,
    background_tasks: BackgroundTasks,
):
    try:

        request_json = (
            payload.model_dump()
        )

        service = (
            ConflictAnalysisJobService()
        )

        job = service.create(
            conflict_id=None,

            horizon_days=
                payload.horizon_days,

            lookback_days=
                payload.lookback_days,

            ripple_depth=
                payload.ripple_depth,

            preferred_provider=
                "NVIDIA",

            preferred_model=
                "nvidia/nemotron-3-ultra-550b-a55b",

            request_mode=
                "agent_selection",

            request_json=
                request_json,
        )

        background_tasks.add_task(
            service.run,
            str(job["id"]),
        )

        return {
            "status":
                "success",

            "data": {
                "analysis_id":
                    str(job["id"]),

                "status":
                    "queued",

                "request_mode":
                    "agent_selection",

                "selection":
                    request_json,
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
