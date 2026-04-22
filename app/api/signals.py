from fastapi import APIRouter
from app.services.curated_signals_service import generate_curated_signals

router = APIRouter(prefix="/signals", tags=["signals"])

@router.get("/test")
def test_signals():
    return {"status": "signals route working"}

@router.get("/curated")
def curated_signals(limit: int = 10, query: str | None = None):
    return generate_curated_signals(limit=limit, query=query)
