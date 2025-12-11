import aiohttp
import base64
import json
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from app.config import settings
from app.services.error_handler import ErrorHandler, ErrorType

logger = logging.getLogger(__name__)

class ABBYYClientException(Exception):
    pass

class ABBYYRetryableError(ABBYYClientException):
    pass

class ABBYYFatalError(ABBYYClientException):
    pass

class ABBYYClient:

    ENDPOINT = "/FlexiCapture12/Server/FCAuth/API/v1/Json"
    
    def __init__(
        self,
        server_url: str = None,
        username: str = None,
        password: str = None,
        tenant: str = None
    ):
        self.server_url = server_url or settings.ABBYY_SERVER_URL
        self.username = username or settings.ABBYY_USERNAME
        self.password = password or settings.ABBYY_PASSWORD
        self.tenant = tenant or settings.ABBYY_TENANT
        self.http_client = None
        
        logger.info(f"ABBYYClient initialized (server={self.server_url})")
    
    def _get_auth_header(self) -> str:
        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"
    
    async def _call_api(self, method_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        
        if not self.http_client:
            self.http_client = aiohttp.ClientSession()
        
        # build URL with tenant
        url = f"{self.server_url}{self.ENDPOINT}"
        if self.tenant:
            url += f"?tenant={self.tenant}"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": self._get_auth_header()
        }
        
        payload = {
            "MethodName": method_name,
            "Params": params
        }
        
        try:
            logger.debug(f"[ABBYY] {method_name} (tenant={self.tenant})")
            
            async with self.http_client.post(
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                data = await response.json()
                
                if not data.get('IsSuccessful'):
                    error_msg = data.get('ErrorMessage', 'Unknown error')
                    logger.error(f"[ABBYY] {method_name} failed: {error_msg}")
                    raise ABBYYFatalError(error_msg)
                
                logger.debug(f"[ABBYY] {method_name} succeeded")
                return data.get('Value')
        
        except asyncio.TimeoutError as e:
            logger.error(f"[ABBYY] {method_name} timeout")
            raise ABBYYRetryableError(f"Request timeout: {str(e)}")
        
        except aiohttp.ClientError as e:
            logger.error(f"[ABBYY] {method_name} connection error: {str(e)}")
            raise ABBYYRetryableError(f"Connection error: {str(e)}")
        
        except Exception as e:
            logger.error(f"[ABBYY] {method_name} error: {str(e)}", exc_info=True)
            raise
    
    # session
    
    #open session
    async def open_session(self) -> str:
        result = await self._call_api("OpenSession", {
            "roleType": 3,  # Operator role
            "stationType": 2  # Document type
        })
        session_id = result['Id']
        logger.info(f"Session opened: {session_id}")
        return session_id
    
    #close abby session
    async def close_session(self, session_id: str) -> bool:
        await self._call_api("CloseSession", {"sessionId": session_id})
        logger.info(f"Session closed: {session_id}")
        return True
    
    # batch mgmt
    
    # create new batch
    async def add_batch(self, session_id: str, project_id: int, batch_name: str) -> int:
        result = await self._call_api("AddNewBatch", {
            "sessionId": session_id,
            "projectId": project_id,
            "ownerId": -1,
            "batch": {
                "Id": 0,
                "Name": batch_name,
                "ProjectId": project_id,
                "BatchTypeId": 1,
                "Priority": 0,
                "Description": "Document Processing"
            }
        })
        batch_id = result['Id']
        logger.info(f"Batch created: {batch_id}")
        return batch_id
    
    #open batch
    async def open_batch(self, session_id: str, batch_id: int) -> bool:
        await self._call_api("OpenBatch", {
            "sessionId": session_id,
            "batchId": batch_id
        })
        logger.debug(f"Batch opened: {batch_id}")
        return True
    
    #close batch
    async def close_batch(self, session_id: str, batch_id: int) -> bool:
        await self._call_api("CloseBatch", {
            "sessionId": session_id,
            "batchId": batch_id
        })
        logger.debug(f"Batch closed: {batch_id}")
        return True
    
    # docs mgmt
    
    #add doc to batch
    async def add_document(
        self,
        session_id: str,
        batch_id: int,
        file_content_base64: str,
        document_name: str
    ) -> int:
        result = await self._call_api("AddNewDocument", {
            "sessionId": session_id,
            "previousItemId": 0,
            "excludeFromAutomaticAssembling": False,
            "document": {
                "Id": None,
                "BatchId": batch_id,
                "ParentId": None,
                "ChildrenOrder": [],
                "Pages": []
            },
            "file": {
                "Name": document_name,
                "Bytes": file_content_base64
            }
        })
        doc_id = result['Id']
        logger.info(f"Document added: {doc_id} (batch={batch_id})")
        return doc_id
    
    # submit batch    
    async def process_batch(self, session_id: str, batch_id: int) -> str:

        result = await self._call_api("ProcessBatch", {
            "sessionId": session_id,
            "batchId": batch_id
        })
        status = result if isinstance(result, str) else result.get('Status', 'Processing')
        logger.info(f"Batch submitted for processing: {batch_id} (status={status})")
        return status
    
# status/result after processing
    
    async def get_batch_status(self, batch_id: int) -> Dict[str, Any]:
        result = await self._call_api("GetBatch", {"batchId": batch_id})
        
        return {
            'status': result.get('Status'),  #processing, completed, err
            'progress': result.get('ProcessingPercentage', 0),
            'error_message': result.get('ErrorMessage'),
            'extracted_data': result.get('ExtractedData')
        }
    
    async def close(self):
        if self.http_client:
            await self.http_client.close()
            logger.info("HTTP client closed")
