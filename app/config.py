import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    """Simple configuration"""
    
    # API
    API_TITLE: str = "ABBYY OCR Microservice"
    API_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # ABBYY (from Postman collection)
    ABBYY_API_URL: str = os.getenv(
        "ABBYY_API_URL",
        "https://internal-abbyy-bo-dev.ad.dmv.ca.gov/FlexiCapture12/Server/FCAuth/API/v1/Json"
    )
    ABBYY_USERNAME: str = os.getenv("ABBYY_USERNAME", "")
    ABBYY_PASSWORD: str = os.getenv("ABBYY_PASSWORD", "")
    ABBYY_PROJECT_ID: str = os.getenv("ABBYY_PROJECT_ID", "")
    ABBYY_TENANT: str = os.getenv("ABBYY_TENANT", "")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./documents.db")
    
    # Polling
    POLLING_INTERVAL_MINUTES: int = 10
    TIMEOUT_MINUTES: int = 30
    MAX_RETRIES: int = 3
    
    # File storage (for now, local)
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    
    # PRU endpoints (will add later, for now just endpoints)
    PRU_VEHICLE_ENDPOINT: str = os.getenv("PRU_VEHICLE_ENDPOINT", "http://localhost:8000/api/v1/vehicle-registration/ocr-results")
    PRU_DRIVING_LICENSE_ENDPOINT: str = os.getenv("PRU_DRIVING_LICENSE_ENDPOINT", "http://localhost:8000/api/v1/driving-license/ocr-results")
    PRU_RECORD_SUPPRESSION_ENDPOINT: str = os.getenv("PRU_RECORD_SUPPRESSION_ENDPOINT", "http://localhost:8000/api/v1/record-suppression/ocr-results")
    
    model_config = ConfigDict(env_file=".env", extra="ignore")

settings = Settings()