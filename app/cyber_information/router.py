from fastapi import APIRouter

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
        "phase": 1,
        "foundation_version": "cyber-info-foundation-v1",
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
    """Validate the canonical event contract without persisting or propagating it."""
    return {
        "status": "success",
        "valid": True,
        "schema_version": event.schema_version,
        "event": event.model_dump(mode="json"),
    }
