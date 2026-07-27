"""
Profile Cog (Meloxi Bot Spec).
Identity module with Bio, Badges, and Content Card.
"""

import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone

from ui.embeds import create_profile_embed, create_error_embed, create_success_embed, create_info_embed
from utils.permissions import get_user_badges, is_premium, is_no_prefix, is_bot_owner
from database.db import SessionLocal
from database.models import UserProfile
from config.emojis import BADGE_EMOJIS

class Profile(commands.Cog):
    """User profiles & badges."""

    def __init__(self, bot):
        self.bot = bot

    # ==========================================================================
    # 👤 USER COMMANDS
    # ==========================================================================

    @commands.hybrid_command(name="profile", aliases=["pr"])
    async def profile(self, ctx: commands.Context, user: discord.User = None):
        """View a member's profile card."""
        target = user or ctx.author
        await self._render_profile(ctx, target)



    async def _render_profile(self, ctx, target):
        """Internal render logic."""
        now = datetime.now(timezone.utc) # Added for server_join calculation
        mem = None
        server_join = None
        if ctx.guild:
            mem = ctx.guild.get_member(target.id)
            if mem and mem.joined_at:
                joined = mem.joined_at.replace(tzinfo=timezone.utc)
                server_join = self._format_time_delta(now - joined)
        
        member_obj = mem if ctx.guild and mem else (target if isinstance(target, discord.Member) else None)
        from utils.permissions import get_user_badges
        badges = get_user_badges(target.id, ctx.guild, member=member_obj)

        # 2. Fetch DB Data
        import asyncio
        def get_bio():
            db = SessionLocal()
            try:
                up = db.query(UserProfile).filter_by(user_id=str(target.id)).first()
                return up.bio if up else None
            finally: db.close()
            
        bio = await asyncio.to_thread(get_bio)

        # 3. Create Embed
        guild_icon = ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None
        embed = create_profile_embed(
            user=target, 
            badges=badges, 
            bio=bio, 
            bot_user=self.bot.user,
            requester=ctx.author,
            guild_icon_url=guild_icon
        )
        await ctx.send(embed=embed)

    # ==========================================================================
    # 📝 BIO MANAGEMENT
    # ==========================================================================

    @commands.hybrid_group(name="bio", invoke_without_command=True)
    async def bio_group(self, ctx: commands.Context):
        """Manage your biography."""
        await ctx.send_help(ctx.command)

    @bio_group.command(name="set")
    async def bio_set(self, ctx: commands.Context, *, text: str):
        """Set your biography (max 300 chars)."""
        if len(text) > 300:
             await ctx.send(embed=create_error_embed(None, "Please keep your bio under 300 characters.", user=ctx.author), delete_after=10)
             return
             
        db = SessionLocal()
        try:
             user = db.query(UserProfile).filter_by(user_id=str(ctx.author.id)).first()
             if not user: 
                 user = UserProfile(user_id=str(ctx.author.id))
                 db.add(user)
             
             user.bio = text
             db.commit()
             await ctx.send(embed=create_success_embed(None, "Your bio has been saved.", user=ctx.author), delete_after=10)
        finally: db.close()

    @bio_group.command(name="clear")
    async def bio_clear(self, ctx: commands.Context):
        """Remove your biography."""
        db = SessionLocal()
        try:
             user = db.query(UserProfile).filter_by(user_id=str(ctx.author.id)).first()
             if user:
                 user.bio = None
                 db.commit()
             await ctx.send(embed=create_success_embed(None, "Your bio has been cleared.", user=ctx.author), delete_after=10)
        finally: db.close()

    # ==========================================================================
    # 🛡️ BADGE ADMINISTRATION (Developer Only)
    # ==========================================================================

    @commands.hybrid_group(name="badge", invoke_without_command=True)
    async def badge_group(self, ctx: commands.Context):
        """[Admin] Manage User Badges."""
        if not is_bot_owner(ctx.author.id):
            await ctx.send(embed=create_error_embed(None, "Only developers can use this.", user=ctx.author), delete_after=10)
            return
        await ctx.send_help(ctx.command)

    @badge_group.command(name="add")
    async def badge_add(self, ctx: commands.Context, user: discord.User, name: str):
        """Grant a badge (e.g. Developer, Staff)."""
        if not is_bot_owner(ctx.author.id): return
        
        # Resolve Emoji
        key = name.lower()
        emoji = BADGE_EMOJIS.get(key, "✨")
        display_name = name.title()
        
        new_badge_data = {"name": display_name, "emoji": emoji}
        
        db = SessionLocal()
        try:
            profile = db.query(UserProfile).filter_by(user_id=str(user.id)).first()
            if not profile:
                profile = UserProfile(user_id=str(user.id))
                db.add(profile)
            
            # Update Badges (JSON)
            current_badges = list(profile.badges) if profile.badges else []
            # Avoid dupes
            if not any(b.get('name') == display_name for b in current_badges if isinstance(b, dict)):
                current_badges.append(new_badge_data)
                profile.badges = current_badges
                db.commit()
                await ctx.send(embed=create_success_embed(None, f"Successfully added **{display_name}** to {user.mention}", user=ctx.author), delete_after=10)
            else:
                await ctx.send(embed=create_error_embed("Already Has", "This user already has that badge.", user=ctx.author))
        finally: db.close()

    @badge_group.command(name="remove")
    async def badge_remove(self, ctx: commands.Context, user: discord.User, name: str):
        """Remove a badge."""
        if not is_bot_owner(ctx.author.id): return
        
        db = SessionLocal()
        try:
            profile = db.query(UserProfile).filter_by(user_id=str(user.id)).first()
            if not profile or not profile.badges:
                await ctx.send(embed=create_error_embed("Wait", "This user doesn't have any badges.", user=ctx.author))
                return
            
            current_badges = list(profile.badges)
            # Filter out
            new_badges = [b for b in current_badges if isinstance(b, dict) and b.get('name').lower() != name.lower()]
            
            if len(new_badges) < len(current_badges):
                profile.badges = new_badges
                db.commit()
                await ctx.send(embed=create_success_embed(None, f"Removed **{name}** from {user.mention}", user=ctx.author), delete_after=10)
            else:
                 await ctx.send(embed=create_error_embed("Not Found", f"Badge '{name}' not found.", user=ctx.author))

        finally: db.close()

    def _format_time_delta(self, delta) -> str:
        d = delta.days
        if d < 30: return f"{d} days"
        if d < 365: m = d // 30; return f"{m} month{'s' if m>1 else ''}"
        y = d // 365; m = (d % 365) // 30
        return f"{y}y" + (f", {m}m" if m > 0 else "")

async def setup(bot):
    await bot.add_cog(Profile(bot))
