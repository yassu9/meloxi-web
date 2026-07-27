"""
Configuration Settings.
Loaded from environment variables.
"""

# ==============================================================================
# ⚙️ CONFIG
# ==============================================================================

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


def _get_int_env(name: str, default: int = 0) -> int:
    value = os.getenv(name)
    if not value or not value.strip():
        return default
    try:
        return int(value)
    except ValueError:
        return default


# Bot Core
BOT_TOKEN: Optional[str] = os.getenv("BOT_TOKEN")
OWNER_ID: int = _get_int_env("OWNER_ID", 0)
HQ_SERVER_ID: int = _get_int_env("HQ_SERVER_ID", 0)
DEFAULT_PREFIX: str = os.getenv("PREFIX", "!")

# Database

# Database
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "meloxi.db")
DATABASE_URL: str = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = f"sqlite:///{DB_PATH}"

# Integrations
RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET")
RAZORPAY_PLAN_ID: str = os.getenv("RAZORPAY_PLAN_ID")
RAZORPAY_PLAN_ID: str = os.getenv("RAZORPAY_PLAN_ID")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY") # Dual-AI Fallback
LASTFM_API_KEY: str = os.getenv("LASTFM_API_KEY", "ad28dc8b287dabc8f37e309b1d05c203") # Public shared key for dev
MUSICBRAINZ_USER_AGENT: str = os.getenv("MUSICBRAINZ_USER_AGENT", "MeloxiBot/1.0 (contact@meloxi.bot)")
SPOTIFY_CLIENT_ID: str = os.getenv("SPOTIPY_CLIENT_ID") # Matching .env default
SPOTIFY_CLIENT_SECRET: str = os.getenv("SPOTIPY_CLIENT_SECRET")

# Branding
BOT_NAME = "Meloxi"
BOT_TAGLINE = "Your Premium Music Companion."
CREATOR_CREDIT = "Powered by Meloxi"
SUPPORT_SERVER = "https://discord.gg/MjrfT3FEs3"

# Theme (Neon Cyan / Electric Blue)
# Theme (Dark / Minimalist)
COLOR_PRIMARY = 0x2B2D31  # Dark Grey (Discord Embed Default-ish)
COLOR_ACCENT = 0x2B2D31   # Matches Primary for "Invisible" look
COLOR_SUCCESS = 0x00FF9C  # Success Green
COLOR_ERROR = 0xFF3B3B    # Error Red
COLOR_WARNING = 0xFFD166  # Warning Yellow
COLOR_BACKGROUND = 0x050B14 # Dark Background

# Feature Flags (Master Prompt Defaults)
SPOTIFY_ENABLED = True
JIOSAAVN_ENABLED = True
YOUTUBE_ENABLED = True
AI_ENABLED = False # Safe Default: False

JIOSAAVN_GLOBAL_ENABLED = True

DEFAULT_FEATURES = {
    "autodj": False,
    "song_reactions": True,
    "smartskip": False,
    "dj_auto_badge": False,
    "anti_spam": False,
    "auto_announce_channel": False,
    "xp_level_system": False,
    "suggestions": True,
    "suggestions": True,
    "jiosaavn": True,
    "use_ai_enhancement": False # 🤖 Safe Default: False
}

# Badges (UI)
BADGE_EMOJIS = {
    "bot_owner": "👑",
    "server_owner": "🛡️",
    "premium": "💎",
    "no_prefix": "🔓",
    "dj": "🎧",
    "level_5": "🎶",
    "level_10": "🎧",
    "level_20": "🔥",
    "level_30": "🎼",
    "level_50": "👑",
}

LEVEL_BADGES = {
    5: "🎶", 10: "🎧", 20: "🔥", 30: "🎼", 50: "👑"
}