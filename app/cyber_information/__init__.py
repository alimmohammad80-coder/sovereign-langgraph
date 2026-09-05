"""Cyber & Information Operations Intelligence package."""

from fastapi import APIRouter

from .phase4_router import router as information_operations_router
from .router import router as core_router

router = APIRouter()
router.include_router(core_router)
router.include_router(information_operations_router)

__all__ = ["router"]
