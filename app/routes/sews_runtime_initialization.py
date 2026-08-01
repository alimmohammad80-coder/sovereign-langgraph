from fastapi import APIRouter, Depends
from supabase import Client
from app.routes.sews_evidence import get_sews_supabase_client
from app.services.sews_runtime_initialization_service import SEWSRuntimeInitializationService

router = APIRouter(prefix='/api/sews/admin/runtime', tags=['SEWS Runtime Initialization'])

def get_db() -> Client:
    return get_sews_supabase_client()

@router.get('/status')
def runtime_status(db: Client = Depends(get_db)):
    return SEWSRuntimeInitializationService(db).status()

@router.post('/initialize')
def initialize_runtime(payload: dict, db: Client = Depends(get_db)):
    return SEWSRuntimeInitializationService(db).initialize(dry_run=bool(payload.get('dry_run', False)))
