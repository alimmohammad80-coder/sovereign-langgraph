from fastapi import APIRouter, Depends
from supabase import Client
from app.routes.sews_evidence import get_sews_supabase_client
from app.schemas.sews_operations import WarningSupervisorRunRequest, PortfolioSupervisorRunRequest, EvidencePipelineResponse, PortfolioSupervisorRunResponse
from app.services.sews_warning_supervisor import SEWSWarningSupervisor
from app.services.sews_portfolio_supervisor import SEWSPortfolioSupervisor

router = APIRouter(prefix="/api/sews/operations", tags=["SEWS Operations"])

def get_db() -> Client:
    return get_sews_supabase_client()

@router.post("/warning/run", response_model=EvidencePipelineResponse)
async def run_warning(payload: WarningSupervisorRunRequest, db: Client = Depends(get_db)):
    return await SEWSWarningSupervisor(db).run(payload)

@router.post("/portfolio/run", response_model=PortfolioSupervisorRunResponse)
async def run_portfolio(payload: PortfolioSupervisorRunRequest, db: Client = Depends(get_db)):
    return await SEWSPortfolioSupervisor(db).run(payload)
