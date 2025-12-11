import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session as DBSession
from typing import Optional

from app.models import ABBYYSessionCache
from app.services.abbyy_client import ABBYYClient
from app.config import settings

logger = logging.getLogger(__name__)

# to manage abbyy sessions across cycles
class SessionManager:    
    def __init__(self, db: DBSession, abbyy_client: ABBYYClient):
        self.db = db
        self.abbyy_client = abbyy_client
    
    async def get_or_create_session(self) -> str:
        
        #get existing active session
        cached = self.db.query(ABBYYSessionCache).filter(
            ABBYYSessionCache.is_active == True
        ).order_by(ABBYYSessionCache.last_used_at.desc()).first()
        
        if cached:
            # validate session working
            if not cached.is_expired() and not cached.should_close_on_error():
                logger.info(f"Reusing session: {cached.session_id} (age: {self._get_session_age(cached)}h)")
                cached.last_used_at = datetime.utcnow()
                self.db.commit()
                return cached.session_id
            else:
                logger.info(f"Session expired or errored: {cached.session_id}")
                cached.is_active = False
                self.db.commit()
        
        # create new session
        try:
            session_id = await self.abbyy_client.open_session()
            
            cache_entry = ABBYYSessionCache(
                session_id=session_id,
                opened_at=datetime.utcnow(),
                last_used_at=datetime.utcnow(),
                is_active=True,
                tenant=self.abbyy_client.tenant
            )
            self.db.add(cache_entry)
            self.db.commit()
            
            logger.info(f"New session created: {session_id}")
            return session_id
        
        except Exception as e:
            logger.error(f"Failed to create session: {str(e)}", exc_info=True)
            raise

    #close session
    async def close_session(self, session_id: str) -> bool:
        try:
            await self.abbyy_client.close_session(session_id)
            
            cache_entry = self.db.query(ABBYYSessionCache).filter_by(
                session_id=session_id
            ).first()
            
            if cache_entry:
                cache_entry.is_active = False
                self.db.commit()
            
            logger.info(f"Session closed: {session_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error closing session: {str(e)}")
            return False
    
    def mark_session_error(self, session_id: str):
        cache_entry = self.db.query(ABBYYSessionCache).filter_by(
            session_id=session_id
        ).first()
        
        if cache_entry:
            cache_entry.error_count += 1
            if cache_entry.should_close_on_error():
                cache_entry.is_active = False
                logger.warning(f"Session marked inactive due to errors: {session_id}")
            self.db.commit()
    
    #to remove old/expired session from acahe
    def cleanup_expired_sessions(self) -> int:
        expiry_time = datetime.utcnow() - timedelta(hours=settings.SESSION_EXPIRY_HOURS)
        
        expired = self.db.query(ABBYYSessionCache).filter(
            ABBYYSessionCache.opened_at < expiry_time
        ).all()
        
        count = 0
        for session in expired:
            self.db.delete(session)
            count += 1
        
        if count > 0:
            self.db.commit()
            logger.info(f"Cleaned up {count} expired sessions")
        
        return count
    
    def _get_session_age(self, session: ABBYYSessionCache) -> float:
        age = datetime.utcnow() - session.opened_at
        return age.total_seconds() / 3600
