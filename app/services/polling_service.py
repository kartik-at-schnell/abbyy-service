import logging
import base64
import requests
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import DocumentLibrary
from app.services.abbyy_client import ABBYYClient
from app.config import settings

logger = logging.getLogger(__name__)


class RecordTypeValidator:
    """Validate record type and route to correct PRU endpoint"""
    
    VEHICLE_REGISTRATION = "VEHICLE_REGISTRATION"
    DRIVING_LICENSE = "DRIVING_LICENSE"
    RECORD_SUPPRESSION = "RECORD_SUPPRESSION"
    
    @staticmethod
    def get_record_type(document_type: str):
        """Get normalized record type"""
        if not document_type:
            return None
        
        doc_type = document_type.upper().strip()
        
        if "VEHICLE" in doc_type or "VR" in doc_type:
            return RecordTypeValidator.VEHICLE_REGISTRATION
        elif "DRIVING" in doc_type or "LICENSE" in doc_type or "DL" in doc_type:
            return RecordTypeValidator.DRIVING_LICENSE
        elif "SUPPRESSION" in doc_type or "RS" in doc_type:
            return RecordTypeValidator.RECORD_SUPPRESSION
        
        return None
    
    @staticmethod
    def get_pru_endpoint(record_type: str):
        """Get PRU endpoint based on record type"""
        if record_type == RecordTypeValidator.VEHICLE_REGISTRATION:
            return settings.PRU_VEHICLE_ENDPOINT
        elif record_type == RecordTypeValidator.DRIVING_LICENSE:
            return settings.PRU_DRIVING_LICENSE_ENDPOINT
        elif record_type == RecordTypeValidator.RECORD_SUPPRESSION:
            return settings.PRU_RECORD_SUPPRESSION_ENDPOINT
        
        return None


class ABBYYPollingService:
    
    def __init__(self, db: Session):
        self.db = db
        self.abbyy = ABBYYClient()
    
    def run_cycle(self):
        doc = None 
        logger.info("=" * 60)
        logger.info("POLLING CYCLE STARTED")
        logger.info("=" * 60)
        
        try:
            # Step 1: Get next queued document
            doc = self.db.query(DocumentLibrary).filter(
                DocumentLibrary.status == "QUEUED_FOR_ABBYY"
            ).first()
            
            if not doc:
                logger.info("✓ No documents to process")
                logger.info("=" * 60)
                return
            
            logger.info(f"Processing Document ID: {doc.id}")
            logger.info(f"Document Type: {doc.document_type}")
            
            # Step 2: Validate record type
            record_type = RecordTypeValidator.get_record_type(doc.document_type)
            if not record_type:
                logger.error(f"✗ Invalid document type: {doc.document_type}")
                doc.status = "FAILED"
                doc.error_message = f"Invalid record type: {doc.document_type}"
                self.db.commit()
                return
            
            logger.info(f"✓ Record type validated: {record_type}")
            
            # Step 3: Read file and encode to base64
            try:
                with open(doc.file_path, "rb") as f:
                    file_bytes = f.read()
                file_base64 = base64.b64encode(file_bytes).decode("utf-8")
                logger.info(f"✓ File read and encoded: {len(file_bytes)} bytes")
            except FileNotFoundError:
                logger.error(f"✗ File not found: {doc.file_path}")
                doc.status = "FAILED"
                doc.error_message = f"File not found: {doc.file_path}"
                self.db.commit()
                return
            
            # Step 4: Open ABBYY session
            session_id = self.abbyy.open_session()
            
            # Step 5: Create batch
            batch_name = f"Doc-{doc.id}-{datetime.utcnow().timestamp()}"
            batch_id = self.abbyy.add_batch(session_id, batch_name)
            
            # Step 6: Open batch
            self.abbyy.open_batch(session_id, batch_id)
            
            # Step 7: Add document
            doc_name = doc.file_path.split("/")[-1]
            self.abbyy.add_document(session_id, batch_id, file_base64, doc_name)
            
            # Step 8: Close batch
            self.abbyy.close_batch(session_id, batch_id)
            
            # Step 9: Process batch
            self.abbyy.process_batch(session_id, batch_id)
            
            # Step 10: Check status (wait for completion)
            logger.info("Waiting for ABBYY processing...")
            max_wait = 30  # 30 cycles * 10 seconds = 5 minutes max
            for attempt in range(max_wait):
                status_result = self.abbyy.get_batch_status(batch_id)
                
                if status_result["status"] == "completed":
                    logger.info("✓ Processing completed!")
                    extracted_data = status_result["extracted_data"]
                    
                    # Step 11: Send to PRU
                    pru_endpoint = RecordTypeValidator.get_pru_endpoint(record_type)
                    logger.info(f"Sending results to PRU: {pru_endpoint}")
                    
                    try:
                        response = requests.post(
                            pru_endpoint,
                            json={
                                "document_id": doc.id,
                                "record_type": record_type,
                                "extracted_data": extracted_data,
                                "timestamp": datetime.utcnow().isoformat()
                            },
                            timeout=30
                        )
                        
                        if response.status_code == 200:
                            logger.info("✓ Results sent to PRU successfully")
                            doc.status = "COMPLETED"
                            doc.extracted_data = extracted_data
                        else:
                            logger.error(f"✗ PRU returned status {response.status_code}")
                            doc.status = "FAILED"
                            doc.error_message = f"PRU error: {response.status_code}"
                    
                    except requests.exceptions.RequestException as e:
                        logger.error(f"✗ Failed to reach PRU: {str(e)}")
                        doc.status = "FAILED"
                        doc.error_message = f"PRU connection error: {str(e)}"
                    
                    break
                
                elif status_result["status"] == "error":
                    logger.error(f"✗ ABBYY error: {status_result['error_message']}")
                    doc.status = "FAILED"
                    doc.error_message = status_result["error_message"]
                    break
                
                else:
                    logger.debug(f"Processing... {status_result['progress']}%")
                    import time
                    time.sleep(10)
            
            else:
                logger.error("✗ Processing timeout")
                doc.status = "FAILED"
                doc.error_message = "ABBYY processing timeout"
            
            # Step 12: Close session
            self.abbyy.close_session(session_id)
            
            # Update database
            doc.processed_at = datetime.utcnow()
            self.db.commit()
            
            logger.info("=" * 60)
            logger.info(f"CYCLE COMPLETE - Status: {doc.status}")
            logger.info("=" * 60)
        
        except Exception as e:
            logger.error(f"✗ Unexpected error: {str(e)}", exc_info=True)
            if doc:
                doc.status = "FAILED"
                doc.error_message = str(e)
                self.db.commit()
            
            logger.info("=" * 60)