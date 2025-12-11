import logging
from enum import Enum
from typing import Tuple
import asyncio
import aiohttp

logger = logging.getLogger(__name__)

class ErrorType(str, Enum):
    RETRYABLE = "RETRYABLE"
    FATAL = "FATAL"
    TIMEOUT = "TIMEOUT"

class ErrorHandler:    
    RETRYABLE_ERRORS = {
        500, 502, 503, 504, 408,
    }
    
    @staticmethod
    def classify_error(exception: Exception) -> Tuple[ErrorType, str]:
 
        if isinstance(exception, asyncio.TimeoutError):
            return ErrorType.TIMEOUT, "Request timeout"

        if isinstance(exception, (aiohttp.ClientError, ConnectionError)):
            return ErrorType.RETRYABLE, str(exception)

        if isinstance(exception, aiohttp.ClientResponseError):
            if exception.status in ErrorHandler.RETRYABLE_ERRORS:
                return ErrorType.RETRYABLE, f"HTTP {exception.status}"
            else:
                return ErrorType.FATAL, f"HTTP {exception.status}: {exception.message}"

        if isinstance(exception, ValueError):
            return ErrorType.FATAL, str(exception)

        return ErrorType.RETRYABLE, str(exception)
    
    @staticmethod
    def is_retryable(error_type: ErrorType) -> bool:
        return error_type == ErrorType.RETRYABLE
