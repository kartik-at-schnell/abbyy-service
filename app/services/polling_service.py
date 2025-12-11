import logging
import asyncio
import base64
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4
from sqlalchemy.orm import Session as DBSession

from app.models import DocumentLibrary, DocumentProcessingLog
from app.services.abbyy_client import ABBYYClient, ABBYYRetryableError, ABBYYFatalError
from app.services.session_manager import SessionManager
from app.services.error_handler import ErrorHandler, ErrorType
from app.config import settings

logger = logging.getLogger(__name__)

class ABBYYPollingService:    
    def __init__(self, db: DBSession, abbyy_client: ABBYYClient):
        self.db = db
        self.abbyy_client = abbyy_client
        self.session_manager = SessionManager(db, abbyy_client)
        self.error_handler = ErrorHandler()
    
    #main polling cycle
    async def run_cycle(self):
        cycle_id = str(uuid4())[:8]
        cycle_start = datetime.utcnow()
        
        logger.info(f"[CYCLE {cycle_id}] Starting polling cycle")
        
        try:
            session_id = await self.session_manager.get_or_create_session() #get session
            submitted_count = await self._process_queued_documents(cycle_id, session_id)    #submit docs
            completed_count = await self._check_processing_status(cycle_id, session_id) #check status
            timeout_count = await self._handle_timeouts(cycle_id)   #get how many timeouts

            await self.session_manager.cleanup_expired_sessions()
            
            elapsed = (datetime.utcnow() - cycle_start).total_seconds()
            logger.info(
                f"[CYCLE {cycle_id}] Completed: "
                f"{submitted_count} submitted, {completed_count} completed, "
                f"{timeout_count} timed out. Elapsed: {elapsed:.2f}s"
            )
        
        except Exception as e:
            logger.error(f"[CYCLE {cycle_id}] Unexpected error: {str(e)}", exc_info=True)
    

    async def _process_queued_documents(self, cycle_id: str, session_id: str) -> int:
        
        docs = self.db.query(DocumentLibrary).filter(
            DocumentLibrary.status == "QUEUED_FOR_ABBYY"
        ).limit(settings.BATCH_SUBMIT_PER_CYCLE).all()
        
        logger.info(f"[CYCLE {cycle_id}] Found {len(docs)} queued documents")
        submitted = 0
        
        for doc in docs:
            try:
                logger.info(f"[DOC {doc.id}] Submitting to ABBYY")
                
                #create batch
                batch_id = await self.abbyy_client.add_batch(
                    session_id=session_id,
                    project_id=settings.ABBYY_PROJECT_ID,
                    batch_name=f"Batch_Doc{doc.id}_{datetime.utcnow().timestamp()}"
                )
                
                # open batch
                await self.abbyy_client.open_batch(session_id, batch_id)
                
                #encode file
                try:
                    with open(doc.document_url, 'rb') as f:
                        file_content = f.read()
                    file_base64 = base64.b64encode(file_content).decode('utf-8')
                except Exception as e:
                    raise ABBYYFatalError(f"Cannot read file: {str(e)}")
                
                #add document
                await self.abbyy_client.add_document(
                    session_id=session_id,
                    batch_id=batch_id,
                    file_content_base64=file_base64,
                    document_name=doc.document_name
                )

                await self.abbyy_client.close_batch(session_id, batch_id)

                await self.abbyy_client.process_batch(session_id, batch_id)

                doc.status = "SENT_TO_ABBYY"
                doc.abbyy_batch_id = batch_id
                doc.abbyy_submitted_at = datetime.utcnow()
                self.db.commit()
                
                self._log_event(doc.id, "BATCH_SUBMITTED", "QUEUED_FOR_ABBYY", "SENT_TO_ABBYY")
                submitted += 1
                logger.info(f"[DOC {doc.id}] Submitted (batch={batch_id})")
            
            except (ABBYYRetryableError, asyncio.TimeoutError) as e:
                logger.warning(f"[DOC {doc.id}] Retryable error: {str(e)}")
                self._handle_retry(doc, "QUEUED_FOR_ABBYY", str(e))
            
            except ABBYYFatalError as e:
                logger.error(f"[DOC {doc.id}] Fatal error: {str(e)}")
                doc.status = "HOLDING_ZONE"
                doc.abbyy_error_message = str(e)
                self.db.commit()
                self._log_event(doc.id, "ERROR_FATAL", "QUEUED_FOR_ABBYY", "HOLDING_ZONE")
            
            except Exception as e:
                logger.error(f"[DOC {doc.id}] Unexpected error: {str(e)}", exc_info=True)
                doc.status = "HOLDING_ZONE"
                doc.abbyy_error_message = str(e)
                self.db.commit()
        
        return submitted
    
    #check status
    async def _check_processing_status(self, cycle_id: str, session_id: str) -> int:        
        docs = self.db.query(DocumentLibrary).filter(
            DocumentLibrary.status.in_(["SENT_TO_ABBYY", "PROCESSING_BY_ABBYY"])
        ).limit(settings.BATCH_CHECK_PER_CYCLE).all()
        
        logger.info(f"[CYCLE {cycle_id}] Checking {len(docs)} processing documents")
        completed = 0
        
        for doc in docs:
            try:
                batch_status = await self.abbyy_client.get_batch_status(doc.abbyy_batch_id)
                
                logger.debug(
                    f"[DOC {doc.id}] Status: {batch_status['status']}, "
                    f"Progress: {batch_status['progress']}%"
                )
                
                if batch_status['status'] == 'Done':
                    results_json = batch_status.get('extracted_data', {})
                    doc.ocr_response_json = results_json
                    doc.ocr_confidence_score = self._extract_confidence(results_json)
                    doc.abbyy_completed_at = datetime.utcnow()
                    doc.status = "COMPLETED"
                    self.db.commit()
                    
                    logger.info(f"[DOC {doc.id}] Completed (confidence={doc.ocr_confidence_score:.1f}%)")
                    self._log_event(doc.id, "RESULT_RECEIVED", "SENT_TO_ABBYY", "COMPLETED")
                    completed += 1
                
                elif batch_status['status'] == 'Error':
                    doc.status = "HOLDING_ZONE"
                    doc.abbyy_error_message = batch_status.get('error_message', 'Unknown error')
                    self.db.commit()
                    
                    logger.error(f"[DOC {doc.id}] ABBYY error: {doc.abbyy_error_message}")
                    self._log_event(doc.id, "ERROR_FROM_ABBYY", "SENT_TO_ABBYY", "HOLDING_ZONE")
                
                else:
                    doc.status = "PROCESSING_BY_ABBYY"
                    self.db.commit()
            
            except Exception as e:
                logger.error(f"[DOC {doc.id}] Error checking status: {str(e)}", exc_info=True)
        
        return completed
    
    # handle docs stuck in processing for long time
    async def _handle_timeouts(self, cycle_id: str) -> int:        
        timeout_threshold = datetime.utcnow() - timedelta(minutes=settings.TIMEOUT_MINUTES)
        
        docs = self.db.query(DocumentLibrary).filter(
            DocumentLibrary.status == "SENT_TO_ABBYY",
            DocumentLibrary.abbyy_submitted_at < timeout_threshold
        ).all()
        
        logger.info(f"[CYCLE {cycle_id}] Found {len(docs)} timed out documents")
        
        for doc in docs:
            doc.status = "HOLDING_ZONE"
            doc.abbyy_error_message = f"Processing timeout (>{settings.TIMEOUT_MINUTES}min)"
            self.db.commit()
            self._log_event(doc.id, "TIMEOUT", "SENT_TO_ABBYY", "HOLDING_ZONE")
        
        return len(docs)
    
    def _extract_confidence(self, results_json: dict) -> float:
        if not results_json or 'pages' not in results_json:
            return 0.0
        
        confidences = []
        for page in results_json.get('pages', []):
            for field in page.get('fields', []):
                if 'confidence' in field:
                    confidences.append(field['confidence'])
        
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    #handle errs that can be retried
    def _handle_retry(self, doc: DocumentLibrary, current_status: str, error: str):
        
        log_entry = self.db.query(DocumentProcessingLog).filter_by(
            document_id=doc.id
        ).order_by(DocumentProcessingLog.timestamp.desc()).first()
        
        retry_count = (log_entry.retry_count + 1) if log_entry else 1
        
        if retry_count >= settings.MAX_RETRIES:
            doc.status = "HOLDING_ZONE"
            doc.abbyy_error_message = f"Max retries exceeded ({settings.MAX_RETRIES})"
            self.db.commit()
            self._log_event(
                doc.id, "MAX_RETRIES_EXCEEDED", current_status, "HOLDING_ZONE"
            )
        else:
            self._log_event(doc.id, "RETRY", current_status, current_status)

    # log the event
    def _log_event(
        self,
        doc_id: int,
        event: str,
        status_before: str,
        status_after: str
    ):        
        log = DocumentProcessingLog(
            document_id=doc_id,
            event=event,
            status_before=status_before,
            status_after=status_after,
            timestamp=datetime.utcnow(),
            performed_by='system'
        )
        self.db.add(log)
        self.db.commit()
