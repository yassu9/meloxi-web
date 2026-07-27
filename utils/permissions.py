"""
Permission Utilities (Meloxi Bot Spec).
Checks for Owner, Admin, Premium, and No-Prefix access.
"""

from discord import Member, Guild
from datetime import datetime, timezone

from utils.config_manager import ConfigManager
from database.db import SessionLocal
from database.models import UserProfile
from config.settings import OWNER_ID
from config.emojis import BADGE_EMOJIS
from utils.time import ist_now

# ==============================================================================
# 🛡️ PERMISSION CHECKS
# ==============================================================================

def is_bot_owner(user_id: int) -> bool:
    """Check if user is Bot Owner."""
    owner = ConfigManager.get_global_config("owner_id", str(OWNER_ID))
    return str(user_id) == owner

def can_manage_server(member: Member) -> bool:
    """Check Admin permissions."""
    return is_bot_owner(member.id) or member.guild_permissions.administrator or member.id == member.guild.owner_id

def is_premium(user_id: int) -> bool:
    """Check Premium status (True if lifetime OR not expired)."""
    db = SessionLocal()
    try:
        p = db.query(UserProfile).filter_by(user_id=str(user_id)).first()
        if not p or not p.premium: return False
        
        # None = Lifetime
        if p.premium_expires_at is None: return True
        return p.premium_expires_at > ist_now()
    finally: db.close()

def is_no_prefix(user_id: int) -> bool:
    """Check No-Prefix access (True if owner/premium OR lifetime OR not expired)."""
    if is_bot_owner(user_id): return True
    if is_premium(user_id): return True
    
    db = SessionLocal()
    try:
        p = db.query(UserProfile).filter_by(user_id=str(user_id)).first()
        if not p or not p.no_prefix: return False
        
        # None = Lifetime
        if p.np_expires_at is None: return True
        return p.np_expires_at > ist_now()
    finally: db.close()

# ==============================================================================
# 🏅 USER BADGES (MELOXI LOGIC)
# ==============================================================================

def get_user_badges(user_id: int, guild: Guild = None, member: Member = None) -> list:
    """Retrieve all user badges based on Meloxi priority."""
    badges = [f"{BADGE_EMOJIS['bot_user']} Bot User"]
    
    # 1. Manual Global Badges from DB (Dev, Staff, VIP, etc)
    db = SessionLocal()
    try:
        p = db.query(UserProfile).filter_by(user_id=str(user_id)).first()
        if p and p.badges: 
            # p.badges is list of dicts: [{"name": "Developer", "emoji": "..."}]
            # We convert to string format for display
            for b_data in p.badges:
                if isinstance(b_data, dict):
                    emoji = b_data.get("emoji", "")
                    name = b_data.get("name", "")
                    badges.append(f"{emoji} {name}")
                elif isinstance(b_data, str): # Legacy support
                    badges.append(b_data)
    finally: db.close()
    
    # 2. System Auto Badges
    if is_bot_owner(user_id): 
        badges.append(f"{BADGE_EMOJIS['bot_owner']} Bot Owner")
        
    if is_premium(user_id): 
        badges.append(f"{BADGE_EMOJIS['premium']} Premium User")
        
    if is_no_prefix(user_id): 
        badges.append(f"{BADGE_EMOJIS['noprefix']} No Prefix")

    # 3. Server Badges (If User is in Guild)
    if guild:
        member = member or guild.get_member(user_id)
        if member:
            if member.id == guild.owner_id:
                badges.append(f"{BADGE_EMOJIS['server_owner']} Server Owner")
            elif member.guild_permissions.administrator:
                badges.append(f"{BADGE_EMOJIS['admin']} Server Admin")
            elif member.guild_permissions.moderate_members:
                badges.append(f"{BADGE_EMOJIS['mod']} Server Mod")

    # 4. Priority Sorting Map
    priority = {
        "Bot Owner": 1,
        "Developer": 2,
        "Partner": 3,
        "Staff": 4,
        "VIP": 5,
        "Premium User": 6,
        "No Prefix": 7,
        "Server Owner": 8,
        "Server Admin": 9,
        "Server Mod": 10,
        "Bot User": 99
    }
    
    def get_sort_key(badge_str):
        for key, val in priority.items():
            if key in badge_str: return val
        return 99 # Default low priority

    unique_badges = list(set(badges))
    unique_badges.sort(key=get_sort_key)

    return unique_badges
