"""
No-Prefix System.
"""

# ==============================================================================
# 📥 IMPORTS
# ==============================================================================

from datetime import datetime
from database.db import SessionLocal
from database.models import UserProfile
from utils.permissions import is_bot_owner
from utils.logger import logger

# ==============================================================================
# 🔓 MANAGER
# ==============================================================================

class NoPrefixManager:
    """Manages No-Prefix Access."""
    
    @staticmethod
    def add_user(user_id: str, expires_at: datetime = None) -> bool:
        """Grant access."""
        db = SessionLocal()
        try:
            p = db.query(UserProfile).filter_by(user_id=str(user_id)).first()
            if not p:
                p = UserProfile(user_id=str(user_id), no_prefix=True, np_expires_at=expires_at)
                db.add(p)
            else:
                p.no_prefix = True
                p.np_expires_at = expires_at
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to add No-Prefix user {user_id}: {e}")
            db.rollback()
            return False
        finally: db.close()
    
    @staticmethod
    def remove_user(user_id: str) -> bool:
        """Revoke access."""
        db = SessionLocal()
        try:
            p = db.query(UserProfile).filter_by(user_id=str(user_id)).first()
            if p:
                p.no_prefix = False
                db.commit()
            return True
        except:
            db.rollback()
            return False
        finally: db.close()
    
    @staticmethod
    def list_users() -> list:
        """List all IDs."""
        db = SessionLocal()
        try:
            users = db.query(UserProfile).filter_by(no_prefix=True).all()
            return [int(u.user_id) for u in users]
        finally: db.close()
    
    @staticmethod
    def has_no_prefix(user_id: int) -> bool:
        """Check access."""
        if is_bot_owner(user_id): return True
        
        db = SessionLocal()
        try:
            p = db.query(UserProfile).filter_by(user_id=str(user_id)).first()
            return p and p.no_prefix
        finally: db.close()
