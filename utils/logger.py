"""
Logging Utilities.
Standardized Logging System for Meloxi.
"""

# ==============================================================================
# 📥 IMPORTS
# ==============================================================================

import logging
import sys
from datetime import datetime, timezone
from typing import Optional
from discord import Embed
from config.settings import COLOR_PRIMARY

# ==============================================================================
# 🪵 LOGGER SETUP
# ==============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('meloxi')

# ==============================================================================
# 🗄️ DATABASE LOGGING
# ==============================================================================

async def log_to_database(db, log_type: str, message: str, metadata: Optional[dict] = None):
    """Insert audit log."""
    from database.models import BotLog
    def perform_insert():
        entry = BotLog(log_type=log_type, message=message, log_metadata=metadata or {})
        db.add(entry)
        db.commit()
    
    import asyncio
    await asyncio.to_thread(perform_insert)

def create_log_embed(title: str, description: str, color: int = COLOR_PRIMARY) -> Embed:
    """Create Log UI."""
    embed = Embed(title=title, description=description, color=color, timestamp=datetime.now(timezone.utc))
    embed.set_footer(text="System Log")
    return embed
