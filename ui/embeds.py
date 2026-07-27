"""
Embed Utilities for Meloxi.
Consistent UI layout and styling.
"""

# ==============================================================================
# 📥 IMPORTS
# ==============================================================================

from datetime import datetime, timezone
from typing import Optional
from discord import Embed, User, Member

from config.settings import COLOR_PRIMARY, COLOR_SUCCESS, COLOR_ERROR, COLOR_WARNING, BOT_NAME, CREATOR_CREDIT
from config.emojis import (
    EMOJI_SUCCESS, EMOJI_ERROR, EMOJI_WARNING, EMOJI_INFO, EMOJI_LOADING,
    CD, EMOJI_CD, EMOJI_NOTE, EMOJI_NOTES, EMOJI_MIC, EMOJI_HEADPHONES, 
    EMOJI_SATELLITE, EMOJI_USERS, EMOJI_USER, EMOJI_QUEUE, EMOJI_TIME,
    EMOJI_ID, EMOJI_SHIELD, EMOJI_PREMIUM, EMOJI_BADGE, EMOJI_RANK, 
    EMOJI_BIO, EMOJI_JOIN, EMOJI_BABY, EMOJI_XP, section, arrow, EMOJI_PLAYING
)


# --------------------



def _get_user_context(user: Optional[User] = None, member: Optional[Member] = None):
    """Resolve display name and avatar."""
    if member: return member.display_name, member.display_avatar.url
    if user: return user.display_name, user.display_avatar.url
    return None, None

def _set_embed_footer(embed: Embed, user: Optional[User] = None, bot_user: Optional[User] = None, tip: Optional[str] = None, guild_icon_url: Optional[str] = None):
    """Set standardized footer: Requested by <User> | Icon: Server Logo."""
    if not user and not tip: return
    
    footer_text = tip if tip else f"Requested by {user.name}"
    icon_url = guild_icon_url if guild_icon_url else (bot_user.display_avatar.url if bot_user else None)
        
    embed.set_footer(text=footer_text, icon_url=icon_url)

def format_duration(dur, is_live: bool = False) -> str:
    """Format duration safely into m:ss."""
    if is_live: return "LIVE"
    if dur in [None, "None", "", 0, 0.0]: return "0:00"
    try:
        dur_int = int(float(dur))
        if dur_int <= 0: return "0:00"
        return f"{dur_int // 60}:{dur_int % 60:02d}"
    except (ValueError, TypeError):
        return "0:00"

# ==============================================================================
# 🎨 EMBED BUILDERS
# ==============================================================================

def create_embed(
    title: str = None, description: str = None, color: int = COLOR_PRIMARY,
    user: Optional[User] = None, member: Optional[Member] = None, 
    bot_user: Optional[User] = None, context: str = None,
    tip: Optional[str] = None, guild_icon_url: str = None,
    show_footer: bool = False
) -> Embed:
    """Base Embed Factory - Pryton v2.0 Style."""
    embed = Embed(title=title, description=description, color=color)
    
    if show_footer:
        _set_embed_footer(embed, user=user, bot_user=bot_user, tip=tip, guild_icon_url=guild_icon_url)
    return embed

def create_info_embed(title: Optional[str], description: str, user=None, member=None, bot_user=None, guild_icon_url=None, show_footer: bool = False, compact: bool = True) -> Embed:
    """Refined Info Style."""
    if compact and not title:
        embed = create_embed(None, f"{EMOJI_INFO} | {description}", COLOR_PRIMARY, user, member, bot_user, guild_icon_url=guild_icon_url, show_footer=show_footer)
    else:
        embed = create_embed(title, f"> {arrow} {description}", COLOR_PRIMARY, user, member, bot_user, guild_icon_url=guild_icon_url, show_footer=show_footer)
    return embed

def create_success_embed(title: Optional[str], description: str, user=None, member=None, bot_user=None, guild_icon_url=None, show_footer: bool = False, compact: bool = True) -> Embed:
    """Refined Success Style."""
    if compact and not title:
        embed = create_embed(None, f"{EMOJI_SUCCESS} | {description}", COLOR_SUCCESS, user, member, bot_user, guild_icon_url=guild_icon_url, show_footer=show_footer)
    else:
        embed = create_embed(title, f"> {arrow} {description}", COLOR_SUCCESS, user, member, bot_user, guild_icon_url=guild_icon_url, show_footer=show_footer)
    return embed

def create_error_embed(title: Optional[str], description: str, user=None, member=None, bot_user=None, guild_icon_url=None, show_footer: bool = False, compact: bool = True) -> Embed:
    """Refined Error Style."""
    if compact and not title:
        embed = create_embed(None, f"{EMOJI_ERROR} | {description}", COLOR_ERROR, user, member, bot_user, guild_icon_url=guild_icon_url, show_footer=show_footer)
    else:
        embed = create_embed(title, f"> {arrow} {description}", COLOR_ERROR, user, member, bot_user, guild_icon_url=guild_icon_url, show_footer=show_footer)
    return embed

def create_warning_embed(title: Optional[str], description: str, user=None, member=None, bot_user=None, guild_icon_url=None, show_footer: bool = False, compact: bool = True) -> Embed:
    """Refined Warning Style."""
    if compact and not title:
        embed = create_embed(None, f"{EMOJI_WARNING} | {description}", COLOR_WARNING, user, member, bot_user, guild_icon_url=guild_icon_url, show_footer=show_footer)
    else:
        embed = create_embed(title, f"> {arrow} {description}", COLOR_WARNING, user, member, bot_user, guild_icon_url=guild_icon_url, show_footer=show_footer)
    return embed

# ==============================================================================
# 🎵 MUSIC EMBEDS
# ==============================================================================

def create_now_playing_embed(
    song_title: str, duration: str = None, requester: User = None,
    loop: bool = False, progress: float = 0.0, thumbnail: str = None,
    album: str = None, artist: str = None, bot_user: User = None,
    score: int = 0, brain_mode: bool = False,
    listeners: int = 0, status_override: str = None, source: str = None,
    volume: float = 1.0, guild_icon: str = None, queue_len: int = 0
) -> Embed:
    """Now Playing visuals - Premium Professional v3.0."""
    # Author/Header removed for minimalism
    embed = create_embed(None, None, COLOR_PRIMARY, bot_user=bot_user, context=None)
    
    # Title: Simple Header
    embed.title = f"{CD} Now Playing"
    
    desc = []
    
    # 1. TRACK INFORMATION
    desc.append(f"{section} **Song Info**")
    desc.append(f"> {arrow} **Title** : **{song_title}**")
    
    if artist and artist != "Unknown":
        desc.append(f"> {arrow} **Artist**: `{artist}`")
    if album:
        desc.append(f"> {arrow} **Album**: *{album}*")
    desc.append("") 
    
    # 2. PLAYER STATUS
    desc.append(f"{section} **Status**")
    
    status = "Playing" 
    if status_override: status = status_override
    elif loop: status = "Looping"
    
    vol_pct = int(volume * 100)
    
    desc.append(f"> {arrow} **Time**: `{duration if duration != '0:00' else 'LIVE' if status_override == 'LIVE' else 'Unknown'}`")
    desc.append(f"> {arrow} **Volume**: `{vol_pct}%`")
    desc.append(f"> {arrow} **Status**: `{status}`")
    desc.append("")

    # 3. OTHER INFO
    desc.append(f"{section} **Info**")
    
    if listeners > 0:
        desc.append(f"> {arrow} **Listeners**: `{listeners} active`")

    if requester:
        desc.append(f"> {arrow} **Requested by**: `{requester.name}`")
        
    # Queue Count ("request ke niche queue me kitne song he vo show kro count if avilbale")
    if queue_len > 0:
        desc.append(f"> {arrow} **Queue**: `{queue_len} Songs Pending`")
    
    # mode_text = "Brain-AI Active" if brain_mode else "Manual Input"
    # desc.append(f"> {arrow} **Mode**: *{mode_text}*")

    embed.description = "\n".join(desc)
    
    if thumbnail: embed.set_image(url=thumbnail)
    
    # Minimal Footer: Only if guild_icon is provided (Server context)
    if guild_icon:
        embed.set_footer(text="Type song name to play", icon_url=guild_icon)
        
    return embed

def create_queue_embed(current_song=None, queue_list=None, user=None, member=None, bot_user=None) -> Embed:
    """Visualize Queue - Premium Professional v3.0."""
    embed = create_embed("Queue List", None, COLOR_PRIMARY)
    
    desc = []
    
    if current_song:
        title = current_song.get('title', 'Unknown')
        artist = current_song.get('artist') or current_song.get('uploader')
        dur = current_song.get('duration')
        d_str = format_duration(dur, is_live=current_song.get('is_live', False))
        
        desc.append(f"{section} **Playing**")
        desc.append(f"> {arrow} **Name**: **{title}**")
        if artist and artist != "Unknown":
            desc.append(f"> {arrow} **Artist**: `{artist}`")
        desc.append(f"> {arrow} **Time**: `[{d_str}]`")
        desc.append("")
    
    if queue_list:
        try:
            total_duration = sum(int(float(s.get('duration') or 0)) for s in queue_list if str(s.get('duration', '')).replace('.','',1).isdigit())
        except:
            total_duration = 0
        td_str = format_duration(total_duration) if total_duration > 0 else "Unknown"
        
        desc.append(f"{section} **Next Songs**")
        for i, song in enumerate(queue_list[:10]):
            s_title = song.get('title', 'Unknown')
            if len(s_title) > 42: s_title = s_title[:39] + "..."
            s_dur = song.get('duration')
            sd_str = format_duration(s_dur, is_live=song.get('is_live', False))
            desc.append(f"> {arrow} `#{i+1:02d}` **{s_title}** `[{sd_str}]`")
            
        if len(queue_list) > 10:
            desc.append(f"\n> {arrow} *...and {len(queue_list)-10} more in buffer.*")
            
        desc.append("")
        desc.append(f"{section} **Stats**")
        desc.append(f"```yaml\nSongs: {len(queue_list)}\nRemaining: {td_str}\n```")

    elif not current_song:
        desc.append(f"> {arrow} *The queue is empty. Add songs with /play!*")
    
    embed.description = "\n".join(desc)
    return embed

def create_song_added_embed(song, position, user=None, bot_user=None, source=None, count: int = 1) -> Embed:
    """Song Added Confirmation - Premium Professional v3.0 (Polished)."""
    title = song.get("title", "Unknown")
    artist = song.get("artist") or song.get("uploader")
    dur = song.get("duration")
    d_str = format_duration(dur, is_live=song.get('is_live', False))
    
    # Header: Distinct success feel
    embed_title = f"{EMOJI_SUCCESS} " + ("Song Added" if count == 1 else "Playlist Added")
    embed = create_embed(title=embed_title, color=COLOR_SUCCESS, bot_user=bot_user)
    
    desc = []
    # Design: High-Fidelity Metadata
    if count == 1:
        desc.append(f"{section} **Track Details**")
        desc.append(f"> {arrow} **Title**: **{title}**")
        if artist and artist != "Unknown":
            desc.append(f"> {arrow} **Artist**: `{artist}`")
        desc.append(f"> {arrow} **Duration**: `{d_str}`")
    else:
        desc.append(f"{section} **Playlist Details**")
        desc.append(f"> {arrow} **Tracks**: `{count} songs added`")
        desc.append(f"> {arrow} **Source**: `{source or 'External Link'}`")
    
    desc.append("")
    desc.append(f"{section} **Queue Position**")
    pos_text = "Up Next" if position == 1 else f"#{position} in queue"
    desc.append(f"> {arrow} **Status**: `{pos_text}`")
    
    if user:
        desc.append(f"> {arrow} **By**: {user.mention}")

    embed.description = "\n".join(desc)
    
    # Media
    thumb = song.get("thumbnail")
    if thumb: embed.set_thumbnail(url=thumb)
    
    # Footer: Branding & Help
    tip = "💡 Tip: use /suggest for recommendations"
    embed.set_footer(text=f"{BOT_NAME} Music • {tip}", icon_url=user.display_avatar.url if user else None)
    
    return embed

# ==============================================================================
# 👤 PROFILE EMBEDS
# ==============================================================================

def create_profile_embed(user, badges, bio=None, bot_user=None, requester=None, guild_icon_url=None) -> Embed:
    """User Profile Card - Meloxi Bot Spec (Vertical Layout)."""
    # Author/Header restored for identity card style
    embed = create_embed(None, None, COLOR_PRIMARY, bot_user=bot_user, guild_icon_url=guild_icon_url, show_footer=True if requester else False, user=requester)
    embed.set_author(name=f"{user.name}", icon_url=user.display_avatar.url)
    embed.set_thumbnail(url=user.display_avatar.url)
    
    desc = []
    
    # Field 1: Badges
    if badges:
        # Vertical list with arrow prefixes and indentation
        embed.add_field(name=f"{section} **Badges**", value="\n".join([f"> {arrow} {b}" for b in badges]), inline=False)
    else:
        embed.add_field(name=f"{section} **Badges**", value=f"{arrow} No active badges.", inline=False)

    # Field 2: Bio
    bio_text = bio if bio else "No biography set."
    embed.add_field(name=f"{section} **Bio**", value=f"```\n{bio_text}\n```", inline=False)

    return embed
