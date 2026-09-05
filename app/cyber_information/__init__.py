"""Cyber & Information Operations Intelligence package."""

from fastapi import APIRouter

from .phase4_router import router as information_operations_router
from .phase5_router import router as hybrid_fusion_router
from .phase6_router import router as forecasting_router
from .phase7_router import router as integration_router
from .router import router as core_router

router = APIRouter()
router.include_router(core_router)
router.include_router(information_operations_router)
router.include_router(hybrid_fusion_router)
router.include_router(forecasting_router)
router.include_router(integration_router)

__all__ = ["router"]
