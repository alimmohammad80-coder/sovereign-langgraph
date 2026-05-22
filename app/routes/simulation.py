from fastapi import APIRouter
from app.routes.simulation_lab import SimulationLabRequest, run_simulation_lab, simulation_lab_questions

router = APIRouter(prefix="/api/simulation", tags=["Simulation Compatibility"])


@router.get("/health")
async def simulation_health():
    return {
        "status": "online",
        "module": "simulation",
        "message": "Compatibility route forwarding to refined Simulation Lab"
    }


@router.post("/run")
async def run_simulation(request: SimulationLabRequest):
    return await run_simulation_lab(request)


@router.post("/questions")
async def simulation_questions(request: SimulationLabRequest):
    return await simulation_lab_questions(request)
