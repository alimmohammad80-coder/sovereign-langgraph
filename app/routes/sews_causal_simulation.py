from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.routes.sews_evidence import get_sews_supabase_client
from app.schemas.sews_causal_simulation import (
    CausalSimulationRequest,
)
from app.services.sews_causal_simulation_service import (
    SEWSCausalSimulationError,
    SEWSCausalSimulationService,
)


router = APIRouter(
    prefix="/api/sews/operations/causal",
    tags=["SEWS Causal Simulation"],
)


@router.post("/simulate")
def simulate_causal_propagation(
    request: CausalSimulationRequest,
):
    try:
        db = get_sews_supabase_client()

        return SEWSCausalSimulationService(db).simulate(
            problem_key=request.problem_key,
            max_depth=request.max_depth,
            ignore_lags=request.ignore_lags,
            persist=request.persist,
        )
    except SEWSCausalSimulationError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc
