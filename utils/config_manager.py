"""
Configuration Management.
"""

# ==============================================================================
# 📥 IMPORTS
# ==============================================================================

from typing import Any
from database.db import SessionLocal
from database.models import ServerConfig, GlobalConfig
from config.settings import DEFAULT_PREFIX, DEFAULT_FEATURES

# ==============================================================================
# ⚙️ MANAGER CLASS
# ==============================================================================

class ConfigManager:
    """Handles Server & Global configurations."""

    @staticmethod
    def get_server_config(server_id: str) -> ServerConfig:
        """Get or create server config."""
        db = SessionLocal()
        try:
            config = db.query(ServerConfig).filter_by(server_id=str(server_id)).first()
            if not config:
                config = ServerConfig(
                    server_id=str(server_id),
                    prefix=DEFAULT_PREFIX,
                    features=DEFAULT_FEATURES.copy()
                )
                db.add(config)
                db.commit()
            db.refresh(config)
            return config
        finally: db.close()

    @staticmethod
    def get_prefix(server_id: str) -> str:
        db = SessionLocal()
        try:
            # Query directly to avoid detached instance issues
            config = db.query(ServerConfig).filter_by(server_id=str(server_id)).first()
            if config: return config.prefix
            return DEFAULT_PREFIX
        except:
             return DEFAULT_PREFIX
        finally: db.close()

    @staticmethod
    def set_prefix(server_id: str, prefix: str) -> bool:
        db = SessionLocal()
        try:
            config = db.query(ServerConfig).filter_by(server_id=str(server_id)).first()
            if not config:
                 # Create if missing
                 config = ServerConfig(
                    server_id=str(server_id),
                    prefix=prefix,
                    features=DEFAULT_FEATURES.copy()
                 )
                 db.add(config)
            else:
                 config.prefix = prefix
            
            db.commit()
            return True
        except:
            db.rollback()
            return False
        finally: db.close()

    # ==========================================================================
    # 🌍 GLOBAL CONFIG
    # ==========================================================================

    @staticmethod
    def get_global_config(key: str, default: Any = None):
        db = SessionLocal()
        try:
            c = db.query(GlobalConfig).filter_by(key=key).first()
            return c.value if c else default
        finally: db.close()

    @staticmethod
    def set_global_config(key: str, value: str) -> bool:
        db = SessionLocal()
        try:
            c = db.query(GlobalConfig).filter_by(key=key).first()
            if c: c.value = value
            else: db.add(GlobalConfig(key=key, value=str(value)))
            db.commit()
            return True
        except:
            db.rollback()
            return False
        finally: db.close()

    # ==========================================================================
    # 🚩 FEATURES
    # ==========================================================================

    @staticmethod
    def get_feature_flag(server_id: str, feature: str) -> bool:
        return ConfigManager.get_server_config(server_id).features.get(feature, False)

    @staticmethod
    def set_feature_flag(server_id: str, feature: str, enabled: bool) -> bool:
        db = SessionLocal()
        try:
            config = db.query(ServerConfig).filter_by(server_id=str(server_id)).first()
            if not config:
                 # Should create if missing
                 return False
            
            # Force update for JSON field
            new_feats = dict(config.features) if config.features else {}
            new_feats[feature] = enabled
            config.features = new_feats
            
            db.commit()
            return True
        except:
            db.rollback()
            return False
        finally: db.close()