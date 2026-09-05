from fastapi import APIRouter, HTTPException

from .integration_bus import CrossModuleIntegrationBus
from .phase7_models import IntegrationDestination

router = APIRouter(
    prefix="/api/cyber-information/integration",
    tags=["Cyber & Information Cross-Module Integration"],
)

bus = CrossModuleIntegrationBus()


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "phase": 7,
        "integration_version": "platform-intelligence-envelope-v1",
        "destinations": [d.value for d in IntegrationDestination],
    }


@router.post("/plan")
def plan_integration(payload: dict) -> dict:
    raw_destinations = payload.get("destinations")
    try:
        destinations = [IntegrationDestination(d) for d in raw_destinations] if raw_destinations else None
        plan = bus.plan(payload.get("source") or payload, destinations=destinations)
        return {"status": "success", "data": plan.model_dump(mode="json")}
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/deliver-simulated")
def deliver_simulated(payload: dict) -> dict:
    """Validate delivery contracts without writing into downstream modules.

    This endpoint intentionally does not mutate SEWS, Conflict Forecasting, or
    other modules. It verifies route readiness, payload shape, and idempotency keys.
    """
    raw_destinations = payload.get("destinations")
    try:
        destinations = [IntegrationDestination(d) for d in raw_destinations] if raw_destinations else None
        plan = bus.plan(payload.get("source") or payload, destinations=destinations)
        results = [bus.mark_delivered(route, plan.envelope.deduplication_key) for route in plan.routes]
        return {
            "status": "success",
            "mode": "simulated_contract_delivery",
            "data": [r.model_dump(mode="json") for r in results],
        }
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
