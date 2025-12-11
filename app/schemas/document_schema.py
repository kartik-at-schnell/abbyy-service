from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class DocumentStatusEnum(str, Enum):
    QUEUED_FOR_ABBYY = "QUEUED_FOR_ABBYY"
    SENT_TO_ABBYY = "SENT_TO_ABBYY"
    PROCESSING_BY_ABBYY = "PROCESSING_BY_ABBYY"
    COMPLETED = "COMPLETED"
    HOLDING_ZONE = "HOLDING_ZONE"
    FAILED = "FAILED"

class DocumentTypeEnum(str, Enum):
    VR_MASTER = "VR_MASTER"
    VR_UNDERCOVER = "VR_UNDERCOVER"
    VR_FICTITIOUS = "VR_FICTITIOUS"
    DL_ORIGINAL = "DL_ORIGINAL"
    RS_MASTER = "RS_MASTER"

class DocumentUploadRequest(BaseModel):
    document_name: str = Field(..., min_length=1, max_length=255)
    document_type: DocumentTypeEnum
    created_by: int

class DocumentResponse(BaseModel):
    id: int
    document_name: str
    document_type: str
    status: str
    created_at: datetime
    abbyy_submitted_at: Optional[datetime] = None
    abbyy_completed_at: Optional[datetime] = None
    ocr_confidence_score: Optional[float] = None
    
    class Config:
        from_attributes = True

class DocumentDetailResponse(DocumentResponse):
    document_url: str
    document_size: float
    abbyy_batch_id: Optional[int] = None
    abbyy_error_message: Optional[str] = None
    ocr_response_json: Optional[Dict[str, Any]] = None

class DocumentProcessingLogResponse(BaseModel):
    id: int
    event: str
    status_before: Optional[str]
    status_after: Optional[str]
    timestamp: datetime
    retry_count: int
    notes: Optional[str]
    
    class Config:
        from_attributes = True

class DocumentListResponse(BaseModel):
    total: int
    items: List[DocumentResponse]
