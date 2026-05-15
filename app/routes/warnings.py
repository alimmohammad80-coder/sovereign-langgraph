from fastapi import APIRouter
from app.services.warning_engine_service import generate_strategic_warning

router = APIRouter(
    prefix="/api/warnings",
    tags=["Strategic Warnings"]
)

@router.post("/generate")
def generate(country: str = "China"):
    return generate_strategic_warning(country=country)
