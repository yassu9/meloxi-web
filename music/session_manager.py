"""
Session Management.
"""

# ==============================================================================
# 📥 IMPORTS
# ==============================================================================

from typing import Dict, Optional
from datetime import datetime, timedelta, timezone
from discord import Message

# ==============================================================================
# 🕒 SESSION MANAGER
# ==============================================================================

class SessionManager:
    """Manages interactive menu sessions."""
    
    def __init__(self):
        self.sessions: Dict[int, Dict] = {}
        self.timeout = timedelta(minutes=10)
    
    def create_session(self, user_id: int, message: Message, session_type: str = "help") -> str:
        """Start tracking a user session."""
        sid = f"{user_id}_{int(datetime.now(timezone.utc).timestamp())}"
        self.sessions[user_id] = {
            'session_id': sid,
            'message': message,
            'type': session_type,
            'created_at': datetime.now(timezone.utc),
            'last_activity': datetime.now(timezone.utc)
        }
        return sid
    
    def get_session(self, user_id: int) -> Optional[Dict]:
        """Retrieve active session."""
        session = self.sessions.get(user_id)
        if session:
            # Expiry Check
            if datetime.now(timezone.utc) - session['last_activity'] > self.timeout:
                del self.sessions[user_id]
                return None
            session['last_activity'] = datetime.now(timezone.utc)
        return session
    
    def update_session(self, user_id: int, **kwargs):
        """Update session state."""
        if user_id in self.sessions:
            self.sessions[user_id].update(kwargs)
            self.sessions[user_id]['last_activity'] = datetime.now(timezone.utc)
    
    def delete_session(self, user_id: int):
        """End session."""
        if user_id in self.sessions:
            del self.sessions[user_id]
    
    def cleanup_expired(self):
        """Purge stale sessions."""
        now = datetime.now(timezone.utc)
        expired = [
            uid for uid, s in self.sessions.items()
            if now - s['last_activity'] > self.timeout
        ]
        for uid in expired: del self.sessions[uid]
    
    async def disable_session_buttons(self, user_id: int):
        """Visual cleanup for expired menus."""
        session = self.get_session(user_id)
        if session and session.get('message'):
            try:
                view = session['message'].view
                if view:
                    for item in view.children: item.disabled = True
                    await session['message'].edit(view=view)
            except: pass
