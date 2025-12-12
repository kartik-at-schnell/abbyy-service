from .routes import admin, documents
from fastapi import APIRouter

router = APIRouter()

router.include_router(documents.router, prefix="/documents", tags=["documents"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])

