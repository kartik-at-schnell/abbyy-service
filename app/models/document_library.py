from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import BaseModel

#to track document while performing OCR
class DocumentLibrary(BaseModel):
    """Document tracking with ABBYY integration"""
    __tablename__ = "document_library"

    document_name = Column(String(255), nullable=False, index=True)
    document_type = Column(String(50), nullable=False, index=True)
    document_url = Column(String(512), nullable=False)
    document_size = Column(Float, nullable=True) 
    # processing status
    status = Column(
        String(50),
        default="QUEUED_FOR_ABBYY",
        nullable=False,
        index=True
    )
    abbyy_session_id = Column(String(100), nullable=True, index=True)
    abbyy_batch_id = Column(Integer, nullable=True, index=True)
    abbyy_document_id = Column(Integer, nullable=True)
    abbyy_submitted_at = Column(DateTime, nullable=True)
    abbyy_completed_at = Column(DateTime, nullable=True)
    abbyy_error_message = Column(Text, nullable=True)
    ocr_response_json = Column(JSON, nullable=True)
    ocr_confidence_score = Column(Float, nullable=True)
    master_record_id = Column(Integer, nullable=True)
    master_record_type = Column(String(50), nullable=True)
    created_by = Column(Integer, nullable=True)
    modified_by = Column(Integer, nullable=True)
    is_archived = Column(Boolean, default=False, nullable=False)
    
    # relationships
    processing_logs = relationship(
        "DocumentProcessingLog",
        back_populates="document",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<DocumentLibrary(id={self.id}, name={self.document_name}, status={self.status})>"

# for audit trail
class DocumentProcessingLog(BaseModel):
    __tablename__ = "document_processing_log"
    
    document_id = Column(Integer, ForeignKey("document_library.id"), nullable=False, index=True)
    event = Column(String(100), nullable=False, index=True)
    status_before = Column(String(50), nullable=True)
    status_after = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    details = Column(JSON, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    next_retry_at = Column(DateTime, nullable=True)
    performed_by = Column(String(50), default="system", nullable=False)
    notes = Column(Text, nullable=True)
    
    # Relationships
    document = relationship("DocumentLibrary", back_populates="processing_logs")
    
    def __repr__(self):
        return f"<DocumentProcessingLog(doc_id={self.document_id}, event={self.event})>"
