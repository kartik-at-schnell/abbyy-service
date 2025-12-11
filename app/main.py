# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db, SessionLocal
from app.services.abbyy_client import ABBYYClient
from app.services.polling_service import ABBYYPollingService

# logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("Starting PRU Backend")
    init_db()
    
    db = SessionLocal()
    abbyy_client = ABBYYClient()
    polling_service = ABBYYPollingService(db, abbyy_client)
    
    scheduler.add_job(
        polling_service.run_cycle,
        'interval',
        minutes=settings.POLLING_INTERVAL_MINUTES,
        id='abbyy_polling'
    )
    scheduler.start()
    logger.info(f"polling every {settings.POLLING_INTERVAL_MINUTES} minutes")
    
    yield
    
    logger.info("hutting down")
    scheduler.shutdown()
    db.close()

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import documents, admin, health
app.include_router(documents.router)
app.include_router(admin.router)
app.include_router(health.router)


@app.get("/")
async def root():
    return {
        "app": settings.API_TITLE,
        "version": settings.API_VERSION,
        "status": "running"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)