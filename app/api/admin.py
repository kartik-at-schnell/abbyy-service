import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session as DBSession
from datetime import datetime, timedelta

from app.database import get_db
from app.models import DocumentLibrary, ABBYYSessionCache
from app.services.polling_service import ABBYYPollingService
from app.services.session_manager import SessionManager
from app.services.abbyy_client import ABBYYClient
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

abbyy_client = ABBYYClient()

# get active abby session
@router.get("/sessions")
async def get_sessions(db: DBSession = Depends(get_db)):
   
    sessions = db.query(ABBYYSessionCache).filter_by(is_active=True).all()
    
    return {
        "total": len(sessions),
        "sessions": [
            {
                "session_id": s.session_id,
                "opened_at": s.opened_at,
                "last_used_at": s.last_used_at,
                "error_count": s.error_count,
                "tenant": s.tenant
            }
            for s in sessions
        ]
    }
# close ss manually
@router.post("/sessions/{session_id}/close")
async def close_session(
    session_id: str,
    db: DBSession = Depends(get_db)
):
    session_mgr = SessionManager(db, abbyy_client)
    success = await session_mgr.close_session(session_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to close session"
        )
    
    return {"status": "closed", "session_id": session_id}

#rety ocr
@router.post("/retry/{doc_id}")
async def retry_document(
    doc_id: int,
    db: DBSession = Depends(get_db)
):
    doc = db.query(DocumentLibrary).filter_by(id=doc_id).first()
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found"
        )
    
    if doc.status not in ["HOLDING_ZONE", "FAILED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot retry document in status: {doc.status}"
        )
    
    doc.status = "QUEUED_FOR_ABBYY"
    doc.abbyy_error_message = None
    db.commit()
    
    logger.info(f"Document {doc_id} retried by admin")
    
    return {"status": "queued", "document_id": doc_id}

#get processing details
@router.get("/stats")
async def get_stats(db: DBSession = Depends(get_db)):
    statuses = {
        "QUEUED_FOR_ABBYY": 0,
        "SENT_TO_ABBYY": 0,
        "PROCESSING_BY_ABBYY": 0,
        "COMPLETED": 0,
        "HOLDING_ZONE": 0,
        "FAILED": 0
    }
    
    for status, _ in statuses.items():
        count = db.query(DocumentLibrary).filter_by(status=status).count()
        statuses[status] = count
    
    total = sum(statuses.values())
    
    # avg processing time
    completed = db.query(DocumentLibrary).filter_by(
        status="COMPLETED"
    ).filter(
        DocumentLibrary.abbyy_completed_at.isnot(None)
    ).all()
    
    avg_time = None
    if completed:
        times = [
            (doc.abbyy_completed_at - doc.abbyy_submitted_at).total_seconds()
            for doc in completed if doc.abbyy_submitted_at
        ]
        if times:
            avg_time = sum(times) / len(times)
    
    return {
        "total_documents": total,
        "statuses": statuses,
        "avg_processing_time_seconds": avg_time,
        "sessions_active": db.query(ABBYYSessionCache).filter_by(
            is_active=True
        ).count()
    }


# @router.get("/holding-zone")
# async def get_holding_zone(
#     skip: int = Query(0, ge=0),
#     limit: int = Query(50, ge=1, le=100),
#     db: DBSession = Depends(get_db)
# ):
#     query = db.query(DocumentLibrary).filter_by(status="HOLDING_ZONE")
#     total = query.count()
#     docs = query.offset(skip).limit(limit).all()
    
#     return {
#         "total": total,
#         "documents": [
#             {
#                 "id": doc.id,
#                 "name": doc.document_name,
#                 "type": doc.document_type,
#                 "error": doc.abbyy_error_message,
#                 "submitted_at": doc.abbyy_submitted_at,
#                 "created_at": doc.created_at
#             }
#             for doc in docs
#         ]
#     }

#clenup
@router.delete("/cleanup/sessions")
async def cleanup_sessions(db: DBSession = Depends(get_db)):
    session_mgr = SessionManager(db, abbyy_client)
    count = session_mgr.cleanup_expired_sessions()
    
    return {"cleaned_up": count}
