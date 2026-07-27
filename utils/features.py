"""
Feature Flags.
Managed via ConfigManager.
"""

# ==============================================================================
# 📥 IMPORTS
# ==============================================================================

from typing import Dict
from utils.config_manager import ConfigManager

# ==============================================================================
# 🚩 FEATURE MANAGER
# ==============================================================================

class FeatureManager:
    """Feature toggle system."""
    
    AVAILABLE_FEATURES = {
        "autodj": "AutoDJ",
        "dj_auto_badge": "Auto DJ Badge",
        "anti_spam": "Anti Spam",
        "xp_level_system": "XP & Levels",
        "suggestions": "Suggestions",
        "jiosaavn": "JioSaavn Support"
    }
    
    @staticmethod
    def is_enabled(server_id: str, feature: str) -> bool:
        """Check status."""
        return ConfigManager.get_feature_flag(server_id, feature)
    
    @staticmethod
    def set_enabled(server_id: str, feature: str, enabled: bool) -> bool:
        """Update toggle."""
        return ConfigManager.set_feature_flag(server_id, feature, enabled)
    
    @staticmethod
    def get_all_features(server_id: str) -> Dict[str, bool]:
        """List all flags."""
        config = ConfigManager.get_server_config(server_id)
        return config.features or {}
