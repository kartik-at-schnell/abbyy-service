from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import Any
from ..schemas.document_schema import DocumentCreate, DocumentResponse

router = APIRouter()


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...)) -> Any:
    # minimal stub: in real app, save file and create DB record
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    return JSONResponse({"id": 1, "filename": file.filename, "status": "NEW", "created_at": None})

