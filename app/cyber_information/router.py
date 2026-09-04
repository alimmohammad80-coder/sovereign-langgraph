from fastapi import APIRouter, HTTPException, Query

from .collectors import (
    AbuseIpDbCollector,
    CisaAdvisoryCollector,
    CisaKevCollector,
    GdeltCollector,
    MitreAttackCollector,
    NvdCollector,
    UrlhausCollector,
)
from .collectors.base import CollectorError
from .confidence import assess_confidence
from .models import CrossModuleEvent
from .ontology import ontology_manifest

router = APIRouter(prefix="/api/cyber-information", tags=["Cyber & Information Operations"])


def _upstream_error(exc: CollectorError) -> HTTPException:
    return HTTPException(status_code=502, detail=str(exc))


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "module": "cyber_information_operations",
        "phase": 2,
        "foundation_version": "cyber-info-foundation-v1",
        "collector_version": "cyber-info-collectors-v2",
        "live_sources": [
            "cisa_kev", "cisa_advisories", "nvd", "mitre_attack",
            "gdelt", "urlhaus", "abuseipdb",
        ],
        "standards": ["stix_2_x", "taxii_2_x"],
    }


@router.get("/ontology")
def get_ontology() -> dict:
    return {"status": "success", "data": ontology_manifest()}


@router.get("/confidence/example")
def confidence_example() -> dict:
    assessment = assess_confidence(
        evidence_quality=0.9, source_diversity=0.8, corroboration=0.85,
        analytic_uncertainty=0.2,
        rationale="Example only; validates the deterministic Phase 1 confidence contract.",
    )
    return {"status": "success", "data": assessment.model_dump()}


@router.post("/events/validate")
def validate_cross_module_event(event: CrossModuleEvent) -> dict:
    return {"status": "success", "valid": True, "schema_version": event.schema_version, "event": event.model_dump(mode="json")}


@router.get("/collectors/cisa-kev")
async def collect_cisa_kev(limit: int = Query(default=100, ge=1, le=1000)) -> dict:
    try:
        return {"status": "success", "data": await CisaKevCollector().collect(limit=limit)}
    except CollectorError as exc:
        raise _upstream_error(exc) from exc


@router.get("/collectors/cisa-advisories")
async def collect_cisa_advisories(limit: int = Query(default=100, ge=1, le=500)) -> dict:
    try:
        return {"status": "success", "data": await CisaAdvisoryCollector().collect(limit=limit)}
    except CollectorError as exc:
        raise _upstream_error(exc) from exc


@router.get("/collectors/nvd")
async def collect_nvd(hours: int = Query(default=24, ge=1, le=120), limit: int = Query(default=100, ge=1, le=2000)) -> dict:
    try:
        return {"status": "success", "data": await NvdCollector().collect_recent(hours=hours, limit=limit)}
    except CollectorError as exc:
        raise _upstream_error(exc) from exc


@router.get("/collectors/mitre-attack")
async def collect_mitre_attack(object_type: str | None = None, limit: int = Query(default=500, ge=1, le=5000)) -> dict:
    try:
        return {"status": "success", "data": await MitreAttackCollector().collect(object_type=object_type, limit=limit)}
    except CollectorError as exc:
        raise _upstream_error(exc) from exc


@router.get("/collectors/gdelt")
async def collect_gdelt(query: str = Query(min_length=2, max_length=300), limit: int = Query(default=50, ge=1, le=250)) -> dict:
    try:
        return {"status": "success", "data": await GdeltCollector().search(query=query, max_records=limit)}
    except CollectorError as exc:
        raise _upstream_error(exc) from exc


@router.get("/collectors/urlhaus")
async def collect_urlhaus(limit: int = Query(default=100, ge=1, le=1000)) -> dict:
    try:
        return {"status": "success", "data": await UrlhausCollector().collect_recent(limit=limit)}
    except CollectorError as exc:
        raise _upstream_error(exc) from exc


@router.get("/collectors/abuseipdb/{ip_address}")
async def check_abuseipdb(ip_address: str, max_age_days: int = Query(default=90, ge=1, le=365)) -> dict:
    try:
        return {"status": "success", "data": await AbuseIpDbCollector().check(ip_address=ip_address, max_age_days=max_age_days)}
    except CollectorError as exc:
        raise _upstream_error(exc) from exc
