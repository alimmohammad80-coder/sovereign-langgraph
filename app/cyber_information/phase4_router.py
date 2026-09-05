from fastapi import APIRouter, HTTPException, Query

from .information_engine import (
    analyze_information_environment,
    assess_coordination,
    assess_propagation,
    build_campaign,
    cluster_observations,
    observation_from_record,
    trace_evolution,
)
from .phase4_models import InformationObservation, NarrativeCluster

router = APIRouter(
    prefix="/api/cyber-information/information-operations",
    tags=["Information Operations Intelligence"],
)


@router.get("/health")
def phase4_health() -> dict:
    return {
        "status": "ok",
        "phase": 4,
        "engine_version": "information-operations-engine-v1",
        "capabilities": [
            "narrative_clustering",
            "narrative_evolution",
            "propagation_assessment",
            "coordination_indicators",
            "information_campaign_assessment",
        ],
    }


@router.post("/observations/normalize")
def normalize_observation(record: dict) -> dict:
    observation = observation_from_record(record)
    return {"status": "success", "data": observation.model_dump(mode="json")}


@router.post("/narratives/cluster")
def cluster_narratives(
    observations: list[InformationObservation],
    threshold: float = Query(default=0.45, ge=0.1, le=0.95),
) -> dict:
    clusters = cluster_observations(observations, threshold=threshold)
    return {
        "status": "success",
        "count": len(clusters),
        "data": [cluster.model_dump(mode="json") for cluster in clusters],
    }


@router.post("/narratives/analyze")
def analyze_narratives(payload: dict, threshold: float = Query(default=0.45, ge=0.1, le=0.95)) -> dict:
    records = payload.get("records", [])
    if not isinstance(records, list):
        raise HTTPException(status_code=422, detail="records must be a list")
    return {"status": "success", "data": analyze_information_environment(records, threshold=threshold)}


@router.post("/narratives/evolution")
def narrative_evolution(payload: dict) -> dict:
    cluster = NarrativeCluster.model_validate(payload.get("cluster", {}))
    observations = [InformationObservation.model_validate(item) for item in payload.get("observations", [])]
    return {"status": "success", "data": trace_evolution(cluster, observations).model_dump(mode="json")}


@router.post("/narratives/propagation")
def narrative_propagation(payload: dict) -> dict:
    cluster = NarrativeCluster.model_validate(payload.get("cluster", {}))
    observations = [InformationObservation.model_validate(item) for item in payload.get("observations", [])]
    return {"status": "success", "data": assess_propagation(cluster, observations).model_dump(mode="json")}


@router.post("/coordination/assess")
def coordination_assessment(payload: dict) -> dict:
    cluster = NarrativeCluster.model_validate(payload.get("cluster", {}))
    observations = [InformationObservation.model_validate(item) for item in payload.get("observations", [])]
    return {"status": "success", "data": assess_coordination(cluster, observations).model_dump(mode="json")}


@router.post("/campaigns/build")
def campaign_assessment(payload: dict) -> dict:
    cluster = NarrativeCluster.model_validate(payload.get("cluster", {}))
    observations = [InformationObservation.model_validate(item) for item in payload.get("observations", [])]
    propagation = assess_propagation(cluster, observations)
    coordination = assess_coordination(cluster, observations)
    campaign = build_campaign(cluster, propagation, coordination)
    return {"status": "success", "data": campaign.model_dump(mode="json")}
