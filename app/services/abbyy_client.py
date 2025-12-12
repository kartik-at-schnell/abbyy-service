import requests
import base64
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class ABBYYClient:
    """Simple ABBYY API client - follows Postman collection"""
    
    def __init__(self):
        self.base_url = settings.ABBYY_API_URL
        self.username = settings.ABBYY_USERNAME
        self.password = settings.ABBYY_PASSWORD
        self.project_id = settings.ABBYY_PROJECT_ID
        self.tenant = settings.ABBYY_TENANT
    
    def _get_auth_header(self):
        """Get Basic Auth header"""
        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"
    
    def _call_api(self, method_name: str, params: dict):
        """Call ABBYY API"""
        url = f"{self.base_url}?tenant={self.tenant}"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": self._get_auth_header()
        }
        
        payload = {
            "MethodName": method_name,
            "Params": params
        }
        
        try:
            logger.debug(f"ABBYY API Call: {method_name}")
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get("IsSuccessful"):
                error_msg = data.get("ErrorMessage", "Unknown error")
                logger.error(f"ABBYY Error: {error_msg}")
                raise Exception(error_msg)
            
            return data.get("Value")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"ABBYY Request Error: {str(e)}")
            raise
    
    def open_session(self):
        """Open ABBYY session"""
        result = self._call_api("OpenSession", {
            "roleType": 3,
            "stationType": 2
        })
        session_id = result.get("Id")
        logger.info(f"✓ Session opened: {session_id}")
        return session_id
    
    def add_batch(self, session_id: str, batch_name: str):
        """Create batch"""
        result = self._call_api("AddNewBatch", {
            "sessionId": session_id,
            "projectId": int(self.project_id),
            "ownerId": -1,
            "batchId": 0,
            "name": batch_name,
            "projectId": int(self.project_id),
            "batchTypeId": 1,
            "priority": 0,
            "description": "Document Processing"
        })
        batch_id = result.get("Id")
        logger.info(f"✓ Batch created: {batch_id}")
        return batch_id
    
    def open_batch(self, session_id: str, batch_id: int):
        """Open batch"""
        self._call_api("OpenBatch", {
            "sessionId": session_id,
            "batchId": batch_id
        })
        logger.debug(f"✓ Batch opened: {batch_id}")
    
    def add_document(self, session_id: str, batch_id: int, file_base64: str, file_name: str):
        """Add document to batch"""
        result = self._call_api("AddNewDocument", {
            "sessionId": session_id,
            "previousItemId": 0,
            "excludeFromAutomaticAssembling": False,
            "documentId": None,
            "batchId": batch_id,
            "parentId": None,
            "childrenOrder": "",
            "pages": "",
            "fileName": file_name,
            "bytes": file_base64
        })
        doc_id = result.get("Id")
        logger.info(f"✓ Document added: {doc_id}")
        return doc_id
    
    def close_batch(self, session_id: str, batch_id: int):
        """Close batch"""
        self._call_api("CloseBatch", {
            "sessionId": session_id,
            "batchId": batch_id
        })
        logger.debug(f"✓ Batch closed: {batch_id}")
    
    def process_batch(self, session_id: str, batch_id: int):
        """Process batch"""
        result = self._call_api("ProcessBatch", {
            "sessionId": session_id,
            "batchId": batch_id
        })
        logger.info(f"✓ Batch processing started: {batch_id}")
        return result
    
    def get_batch_status(self, batch_id: int):
        """Get batch status"""
        result = self._call_api("GetBatch", {"batchId": batch_id})
        
        status = result.get("Status", "processing").lower()
        progress = result.get("ProcessingPercentage", 0)
        
        logger.debug(f"Batch {batch_id} Status: {status} ({progress}%)")
        
        return {
            "status": status,
            "progress": progress,
            "extracted_data": result.get("ExtractedData"),
            "error_message": result.get("ErrorMessage")
        }
    
    def close_session(self, session_id: str):
        """Close session"""
        self._call_api("CloseSession", {"sessionId": session_id})
        logger.info(f"✓ Session closed: {session_id}")