from fastapi import FastAPI, APIRouter
from apscheduler.schedulers.background import BackgroundScheduler
import logging
from contextlib import asynccontextmanager
import pkgutil
import importlib
from pathlib import Path
from typing import Optional

from app.api.routes import admin
from app.api.routes import documents

from app.config import settings
from app.database import init_db, SessionLocal
from app.services.polling_service import ABBYYPollingService

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# global scheduler
scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    
    # Startup
    logger.info("Starting ABBYY OCR Microservice")
    init_db()
    
    db = SessionLocal()
    polling_service = ABBYYPollingService(db)
    
    # Schedule polling job
    scheduler.add_job(
        polling_service.run_cycle,
        "interval",
        minutes=settings.POLLING_INTERVAL_MINUTES,
        id="abbyy_polling"
    )
    scheduler.start()
    logger.info(f"Polling scheduled every {settings.POLLING_INTERVAL_MINUTES} minutes")
    
    yield
    
    # Shutdown
    logger.info("Shutting down")
    scheduler.shutdown()
    db.close()


# Create app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    lifespan=lifespan
)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": settings.API_TITLE}


@app.get("/")
async def root():
    return {
        "service": settings.API_TITLE,
        "version": settings.API_VERSION,
        "status": "running"
    }

router = APIRouter(prefix="/api/abbyy")

router.include_router(admin.router)
router.include_router(documents.router)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)