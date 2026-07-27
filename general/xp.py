"""
XP and Leveling System for Meloxi.
"""

import discord
from discord.ext import commands
from database.db import SessionLocal
from database.models import UserProfile
from config.settings import LEVEL_BADGES, COLOR_ACCENT
from ui.embeds import create_embed
from config.emojis import arrow

XP_PER_SONG = 10
LEVEL_XP = 100

# ==============================================================================
# 🧮 CALCULATIONS / UTILS
# ==============================================================================

def calculate_level(xp: int) -> int:
    return xp // LEVEL_XP

def add_music_xp(user_id: int, amount: int = XP_PER_SONG) -> bool:
    db = SessionLocal()
    try:
        profile = db.query(UserProfile).filter_by(user_id=str(user_id)).first()
        if not profile:
            profile = UserProfile(user_id=str(user_id), xp=0, level=0)
            db.add(profile)
        old_lvl = profile.level
        profile.xp += amount
        profile.level = calculate_level(profile.xp)
        db.commit()
        return profile.level > old_lvl
    finally: db.close()

def get_user_xp_stats(user_id: int) -> dict:
    db = SessionLocal()
    try:
        p = db.query(UserProfile).filter_by(user_id=str(user_id)).first()
        if not p: return {"xp": 0, "level": 0, "next_level_xp": LEVEL_XP, "remaining_xp": LEVEL_XP}
        next_xp = (p.level + 1) * LEVEL_XP
        return {"xp": p.xp, "level": p.level, "next_level_xp": next_xp, "remaining_xp": next_xp - p.xp}
    finally: db.close()

def get_level_badge(level: int) -> str:
    badge = ""
    for lvl in sorted(LEVEL_BADGES.keys()):
        if level >= lvl: badge = LEVEL_BADGES[lvl]
    return badge

def get_user_level(user_id: int) -> int:
    db = SessionLocal()
    try:
        p = db.query(UserProfile).filter_by(user_id=str(user_id)).first()
        return p.level if p else 0
    finally: db.close()

# ==============================================================================
# 🏆 XP COG
# ==============================================================================

class XP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="level", aliases=["xp", "rank"])
    async def level(self, ctx: commands.Context):
        """Check music level."""
        stats = get_user_xp_stats(ctx.author.id)
        badge = get_level_badge(stats['level'])
        embed = create_embed(title=f"{ctx.author.name}'s Rank", description=f"> {arrow} **Level**: `{stats['level']}`\n> {arrow} **XP**: `{stats['xp']} / {stats['next_level_xp']}`\n\n*Keep listening to climb up!*", user=ctx.author, bot_user=self.bot.user, show_footer=True)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="leaderboard", aliases=["lb", "top"])
    async def leaderboard(self, ctx: commands.Context):
        """Global Top 10 Users."""
        db = SessionLocal()
        try:
            users = db.query(UserProfile).order_by(UserProfile.xp.desc()).limit(10).all()
            if not users:
                from ui.embeds import create_error_embed
                await ctx.send(embed=create_error_embed(None, "I don't have any rank data yet.", user=ctx.author), delete_after=10)
                return
            lines = []
            for i, p in enumerate(users, 1):
                try:
                    u = self.bot.get_user(int(p.user_id)) or await self.bot.fetch_user(int(p.user_id))
                    name = u.display_name
                except: name = f"<@{p.user_id}>"
                lines.append(f"**{i}.** **{name}**\n> {arrow} Lvl **{p.level}** • **{p.xp} XP**")
            await ctx.send(embed=create_embed("Top Listeners", "\n\n".join(lines), user=ctx.author, bot_user=self.bot.user, show_footer=True))
        finally: db.close()

async def setup(bot):
    await bot.add_cog(XP(bot))