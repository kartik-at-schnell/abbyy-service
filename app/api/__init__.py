from fastapi import APIRouter

router = APIRouter()

from . import documents, admin, health  # noqa: E402,F401

router.include_router(documents.router, prefix="/documents", tags=["documents"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])
router.include_router(health.router, prefix="/health", tags=["health"])

