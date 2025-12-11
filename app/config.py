import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://user:password@localhost:5432/pru_db"
    )

    ABBYY_SERVER_URL: str = os.getenv(
        "ABBYY_SERVER_URL",
        "https://internal-abbyy-bo-dev.ad.dmv.ca.gov"
    )
    ABBYY_USERNAME: str = os.getenv("ABBYY_USERNAME")
    ABBYY_PASSWORD: str = os.getenv("ABBYY_PASSWORD")
    ABBYY_TENANT: Optional[str] = os.getenv("ABBYY_TENANT")
    ABBYY_PROJECT_ID: int = int(os.getenv("ABBYY_PROJECT_ID", "1"))
    ABBYY_USE_REAL: bool = os.getenv("ABBYY_USE_REAL", "true").lower() == "true"
    
    # polling config
    POLLING_INTERVAL_MINUTES: int = int(os.getenv("POLLING_INTERVAL_MINUTES", "10"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "5"))
    TIMEOUT_MINUTES: int = int(os.getenv("TIMEOUT_MINUTES", "30"))
    BATCH_SUBMIT_PER_CYCLE: int = 5  #submit limit per cycle
    BATCH_CHECK_PER_CYCLE: int = 10   #max documents to check
    
    #storage
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR")
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB"))
    MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024
    
    # logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/app.log")
    
    # application
    ENV: str = os.getenv("ENV")
    DEBUG: bool = ENV == "development"
    
    #api
    API_TITLE: str = "PRU Backend - ABBYY Integration"
    API_VERSION: str = "2.0.0"
    
    # session config
    SESSION_EXPIRY_HOURS: int = 24
    SESSION_ERROR_THRESHOLD: int = 5  # close session if this many errs
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()

# ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)
