from sqlalchemy import Column, String, DateTime, Boolean, Integer
from datetime import datetime, timedelta
from app.models.base import BaseModel
from app.config import settings

#to cahce abbyy session, we can reuse in diffrent cycles
class ABBYYSessionCache(BaseModel):
    __tablename__ = "abbyy_session_cache"
    
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    opened_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    error_count = Column(Integer, default=0, nullable=False)
    tenant = Column(String(100), nullable=True)
    created_by = Column(String(50), default="system", nullable=False)
    
    def is_expired(self) -> bool:
        expiry_time = self.opened_at + timedelta(hours=settings.SESSION_EXPIRY_HOURS)
        return datetime.utcnow() > expiry_time
    
    def should_close_on_error(self) -> bool:
        return self.error_count >= settings.SESSION_ERROR_THRESHOLD
    
    def __repr__(self):
        return f"<ABBYYSessionCache(session_id={self.session_id}, is_active={self.is_active})>"
