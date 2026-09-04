from fastapi import APIRouter, HTTPException, Query

from .collectors import CisaKevCollector, GdeltCollector, NvdCollector
from .collectors.base import CollectorError
from .confidence import assess_confidence
from .models import CrossModuleEvent
from .ontology import ontology_manifest

router = APIRouter(
    prefix="/api/cyber-information",
    tags=["Cyber & Information Operations"],
)


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "module": "cyber_information_operations",
        "phase": 2,
        "foundation_version": "cyber-info-foundation-v1",
        "collector_version": "cyber-info-collectors-v1",
        "live_sources": ["cisa_kev", "nvd", "gdelt"],
    }


@router.get("/ontology")
def get_ontology() -> dict:
    return {"status": "success", "data": ontology_manifest()}


@router.get("/confidence/example")
def confidence_example() -> dict:
    assessment = assess_confidence(
        evidence_quality=0.9,
        source_diversity=0.8,
        corroboration=0.85,
        analytic_uncertainty=0.2,
        rationale="Example only; validates the deterministic Phase 1 confidence contract.",
    )
    return {"status": "success", "data": assessment.model_dump()}


@router.post("/events/validate")
def validate_cross_module_event(event: CrossModuleEvent) -> dict:
    return {
        "status": "success",
        "valid": True,
        "schema_version": event.schema_version,
        "event": event.model_dump(mode="json"),
    }


@router.get("/collectors/cisa-kev")
async def collect_cisa_kev(limit: int = Query(default=100, ge=1, le=1000)) -> dict:
    try:
        data = await CisaKevCollector().collect(limit=limit)
        return {"status": "success", "data": data}
    except CollectorError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/collectors/nvd")
async def collect_nvd(
    hours: int = Query(default=24, ge=1, le=120),
    limit: int = Query(default=100, ge=1, le=2000),
) -> dict:
    try:
        data = await NvdCollector().collect_recent(hours=hours, limit=limit)
        return {"status": "success", "data": data}
    except CollectorError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/collectors/gdelt")
async def collect_gdelt(
    query: str = Query(min_length=2, max_length=300),
    limit: int = Query(default=50, ge=1, le=250),
) -> dict:
    try:
        data = await GdeltCollector().search(query=query, max_records=limit)
        return {"status": "success", "data": data}
    except CollectorError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
