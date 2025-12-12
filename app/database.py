from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from typing import Generator
from app.config import settings
from app.models import Base

# Create database engine with proper configuration
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # ← Now defined in config
    poolclass=NullPool,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def init_db():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get database session for dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def lifespan_startup():
    """Initialize database on startup"""
    init_db()


async def lifespan_shutdown():
    """Cleanup on shutdown"""
    engine.dispose()