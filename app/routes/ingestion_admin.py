from fastapi import APIRouter
from app.services.scheduled_ingestion import run_scheduled_ingestion

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin Ingestion"]
)

@router.post("/run-ingestion")
def run_ingestion():
    try:
        results = run_scheduled_ingestion()
        return {
            "status": "completed",
            "results": results
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
