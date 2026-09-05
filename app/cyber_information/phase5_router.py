from fastapi import APIRouter

from .hybrid_fusion import HybridFusionEngine
from .phase5_models import HybridFusionRequest

router = APIRouter(
    prefix="/api/cyber-information/hybrid-fusion",
    tags=["Cyber & Information Operations - Hybrid Fusion"],
)
engine = HybridFusionEngine()


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "phase": 5,
        "engine_version": "hybrid-fusion-v1",
        "capabilities": [
            "cross_domain_signal_normalization",
            "temporal_convergence",
            "target_convergence",
            "actor_convergence",
            "geographic_convergence",
            "cross_domain_convergence",
            "infrastructure_relevance",
            "hybrid_campaign_assessment",
        ],
    }


@router.post("/assess")
def assess_hybrid_campaign(request: HybridFusionRequest) -> dict:
    result = engine.assess(request)
    return {"status": "success", "data": result.model_dump(mode="json")}


@router.post("/signals/normalize")
def normalize_signals(request: HybridFusionRequest) -> dict:
    signals = engine.signals_from_request(request)
    return {
        "status": "success",
        "count": len(signals),
        "data": [signal.model_dump(mode="json") for signal in signals],
    }
