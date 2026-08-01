from fastapi import APIRouter, Depends
from supabase import Client
from app.routes.sews_evidence import get_sews_supabase_client
from app.sews_bridge.discovery import discover_sources
from app.sews_bridge.orchestrator import SEWSExistingSourcesBridge
from app.sews_bridge.schemas import BridgeRunRequest, BridgeRunResponse, SourceBridgeStatus

router = APIRouter(prefix="/api/sews/integration", tags=["SEWS Existing Sources Bridge"])

def get_db() -> Client:
    return get_sews_supabase_client()

@router.get("/status", response_model=list[SourceBridgeStatus])
def integration_status():
    _, statuses = discover_sources()
    return statuses

@router.post("/run", response_model=BridgeRunResponse)
async def run_integration_bridge(payload: BridgeRunRequest, db: Client = Depends(get_db)):
    return await SEWSExistingSourcesBridge(db).run(payload)
