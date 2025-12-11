import logging
from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException, status
from sqlalchemy.orm import Session as DBSession
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import DocumentLibrary
from app.schemas.document_schema import (
    DocumentUploadRequest,
    DocumentResponse,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentProcessingLogResponse,
    DocumentStatusEnum
)
from app.services.storage_service import StorageService
from app.services.polling_service import ABBYYPollingService
from app.services.abbyy_client import ABBYYClient
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

# Initialize services
storage_service = StorageService()
abbyy_client = ABBYYClient()
polling_service = ABBYYPollingService(None, abbyy_client)

# upload doc for ocr
@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Query(...),
    created_by: int = Query(...),
    db: DBSession = Depends(get_db)
):
    
    try:
        # check file size
        file_content = await file.read()
        if len(file_content) > settings.MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds max size of {settings.MAX_FILE_SIZE_MB}MB"
            )
        
        # check doc type
        try:
            DocumentStatusEnum(document_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid document type: {document_type}"
            )
        
        file_path = storage_service.save_file(
            filename=file.filename,
            content=file_content,
            document_type=document_type
        )
        
        #create document record
        doc = DocumentLibrary(
            document_name=file.filename,
            document_type=document_type,
            document_url=file_path,
            document_size=len(file_content),
            status="QUEUED_FOR_ABBYY",
            created_by=created_by
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        logger.info(f"Document uploaded: {doc.id} ({file.filename})")
        
        return DocumentResponse.from_orm(doc)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload document"
        )

#get details
@router.get("/{doc_id}", response_model=DocumentDetailResponse)
async def get_document(
    doc_id: int,
    db: DBSession = Depends(get_db)
):    
    doc = db.query(DocumentLibrary).filter_by(id=doc_id).first()
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found"
        )
    
    return DocumentDetailResponse.from_orm(doc)

#get logs, processing related
@router.get("/{doc_id}/logs", response_model=List[DocumentProcessingLogResponse])
async def get_document_logs(
    doc_id: int,
    db: DBSession = Depends(get_db)
):    
    from app.models import DocumentProcessingLog
    
    logs = db.query(DocumentProcessingLog).filter_by(
        document_id=doc_id
    ).order_by(DocumentProcessingLog.timestamp.desc()).all()
    
    return [DocumentProcessingLogResponse.from_orm(log) for log in logs]

#get doc status
@router.get("/status/by-status", response_model=DocumentListResponse)
async def get_documents_by_status(
    status: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: DBSession = Depends(get_db)
):
    query = db.query(DocumentLibrary).filter_by(status=status)
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    
    return DocumentListResponse(
        total=total,
        items=[DocumentResponse.from_orm(doc) for doc in items]
    )

#get procesed docs
@router.get("/status/completed", response_model=DocumentListResponse)
async def get_completed_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: DBSession = Depends(get_db)
):
    query = db.query(DocumentLibrary).filter_by(status="COMPLETED")
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    
    return DocumentListResponse(
        total=total,
        items=[DocumentResponse.from_orm(doc) for doc in items]
    )

