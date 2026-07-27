"""
Schema definitions for Meloxi. 
"""

# ==============================================================================
# 📥 IMPORTS
# ==============================================================================

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from datetime import datetime, timezone
from database.db import Base

def utcnow(): return datetime.now(timezone.utc)

# ==============================================================================
# ⚙️ CONFIG MODELS
# ==============================================================================

class ServerConfig(Base):
    """Server-specific settings."""
    __tablename__ = "server_configs"

    server_id = Column(String, primary_key=True)
    prefix = Column(String, default="r!")
    
    # Channels
    music_channel_id = Column(String, nullable=True)
    voice_channel_id = Column(String, nullable=True)
    log_channel_id = Column(String, nullable=True)
    request_channel_id = Column(String, nullable=True)
    request_message_id = Column(String, nullable=True)
    
    # Toggles
    auto_247 = Column(Boolean, default=False)
    music_logs_enabled = Column(Boolean, default=False)
    settings_logs_enabled = Column(Boolean, default=False)
    features = Column(JSON, default={})

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

class GlobalConfig(Base):
    """Bot-wide settings."""
    __tablename__ = "global_config"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

# ==============================================================================
# 👤 USER MODELS
# ==============================================================================

class UserProfile(Base):
    """User stats, XP, and badges."""
    __tablename__ = "user_profiles"

    user_id = Column(String, primary_key=True, index=True)
    
    # XP
    xp = Column(Integer, default=0)
    level = Column(Integer, default=0)
    bio = Column(String, default="Music is my life! 🎧")
    
    # Status
    premium = Column(Boolean, default=False)
    premium_expires_at = Column(DateTime, nullable=True)
    no_prefix = Column(Boolean, default=False)
    np_expires_at = Column(DateTime, nullable=True) # None = Lifetime
    badges = Column(JSON, default=[])

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

class Subscription(Base):
    """Premium keys."""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False)
    subscription_id = Column(String, unique=True, nullable=False)
    plan_id = Column(String, nullable=False)
    status = Column(String, nullable=False)
    started_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

# ==============================================================================
# 📝 LOGS & QUEUES
# ==============================================================================

class BotLog(Base):
    """Internal audit logs."""
    __tablename__ = "bot_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    log_type = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    log_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utcnow)

class MusicQueue(Base):
    """Persistent queue storage."""
    __tablename__ = "music_queues"

    id = Column(Integer, primary_key=True, autoincrement=True)
    server_id = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    duration = Column(Integer, nullable=True)
    requester_id = Column(String, nullable=False)
    position = Column(Integer, nullable=False)
    added_at = Column(DateTime, default=utcnow)

class PlaybackHistory(Base):
    """History of played songs for weighting."""
    __tablename__ = "playback_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    server_id = Column(String, index=True, nullable=False)
    title = Column(String, index=True, nullable=False)
    artist = Column(String, index=True, nullable=False)
    
    # Stats
    play_count = Column(Integer, default=1)
    skip_count = Column(Integer, default=0)
    
    last_played = Column(DateTime, default=utcnow)

class GuildRegistry(Base):
    """Track who added the bot to which server."""
    __tablename__ = "guild_registry"

    server_id = Column(String, primary_key=True)
    inviter_id = Column(String, index=True, nullable=False)
    joined_at = Column(DateTime, default=utcnow)