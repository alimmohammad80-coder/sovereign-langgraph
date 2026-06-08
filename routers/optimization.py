from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

router = APIRouter(prefix="/api/optimization", tags=["Optimization"])


class RouteOption(BaseModel):
    route: str
    cost: float
    delay_days: float
    risk_score: float
    capacity_score: Optional[float] = 100


class SupplyChainOptimizationRequest(BaseModel):
    scenario: str
    objective: str = "minimize risk-adjusted shipping cost"
    max_delay_days: Optional[float] = None
    max_cost_increase_percent: Optional[float] = None
    avoid_high_risk_chokepoints: bool = True
    routes: List[RouteOption]


@router.get("/health")
def optimization_health():
    return {
        "status": "ok",
        "service": "Sovereign Intelligence Optimization Engine",
        "mode": "local_fallback",
        "cuopt_available": False,
        "note": "cuOpt requires NVIDIA CUDA GPU runtime for full production optimization."
    }


@router.post("/supply-chain-route")
def optimize_supply_chain_route(payload: SupplyChainOptimizationRequest):
    """
    Local fallback optimizer.
    Later this can call NVIDIA cuOpt when running on a CUDA/GPU environment.
    """

    scored_routes = []

    for route in payload.routes:
        if payload.max_delay_days is not None and route.delay_days > payload.max_delay_days:
            continue

        if payload.avoid_high_risk_chokepoints and route.risk_score >= 80:
            penalty = 50
        else:
            penalty = 0

        # Simple risk-adjusted cost formula.
        # Lower score is better.
        optimization_score = (
            route.cost * 0.45
            + route.delay_days * 2.5
            + route.risk_score * 0.6
            + penalty
            - route.capacity_score * 0.05
        )

        scored_routes.append({
            "route": route.route,
            "cost": route.cost,
            "delay_days": route.delay_days,
            "risk_score": route.risk_score,
            "capacity_score": route.capacity_score,
            "optimization_score": round(optimization_score, 2)
        })

    if not scored_routes:
        return {
            "status": "no_feasible_route",
            "scenario": payload.scenario,
            "message": "No route satisfies the current constraints.",
            "recommendation": "Relax delay, cost, or chokepoint-risk constraints."
        }

    ranked = sorted(scored_routes, key=lambda x: x["optimization_score"])
    best = ranked[0]

    return {
        "status": "success",
        "scenario": payload.scenario,
        "objective": payload.objective,
        "engine": "local_fallback_optimizer",
        "best_route": best,
        "ranked_routes": ranked,
        "executive_recommendation": (
            f"The preferred route is {best['route']} because it has the best "
            f"risk-adjusted balance of cost, delay, and exposure."
        )
    }
