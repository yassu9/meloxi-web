"""
Owner Control Center for Meloxi.
Restricted commands for bot owners only.
"""

import asyncio
import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta, timezone

from ui.embeds import create_success_embed, create_error_embed, create_embed, create_info_embed
from utils.permissions import is_bot_owner
from utils.config_manager import ConfigManager
from utils.noprefix import NoPrefixManager
from premium.subscriptions import SubscriptionManager
from database.db import SessionLocal
from database.models import UserProfile
from utils.logger import logger
from utils.time import parse_duration, ist_now
from config.emojis import arrow
import config.settings as settings # Fix NameError

class Owner(commands.Cog):
    """Commands for Bot Owners only."""
    
    def __init__(self, bot):
        self.bot = bot
        self.sub_manager = SubscriptionManager()

    # ==========================================================================
    # 👑 OWNER TOOLS
    # ==========================================================================

    @commands.command(name="owncmd", aliases=["ownerhelp"], hidden=True)
    async def owner_help(self, ctx: commands.Context):
        """[Owner] List all Owner-Only commands."""
        if not is_bot_owner(ctx.author.id): return
        
        cmds = [
            "**👑 Owner Commands**",
            f"`{ctx.prefix}owncmd`",
            f"`{ctx.prefix}noprefix` (np) ",
            f"`{ctx.prefix}pm` (premiummanage)",
            f"`{ctx.prefix}rpsync`",
            f"`{ctx.prefix}stats`",
            f"`{ctx.prefix}setowner <id>`",
            f"`{ctx.prefix}sethq <id>`",
            f"`{ctx.prefix}reloadconfig`",
            f"`{ctx.prefix}setglobalprefix`",
            f"`{ctx.prefix}togglesaavn`"
        ]
        
        await ctx.send(embed=create_embed(None, "\n".join(cmds), color=settings.COLOR_PRIMARY, user=ctx.author, bot_user=self.bot.user))

    # @commands.command(name="testbot", hidden=True)
    # async def test_bot(self, ctx: commands.Context):
    #     """[Owner] Simple health check."""
    #     if not is_bot_owner(ctx.author.id): return
        
    #     lat = round(self.bot.latency * 1000)
    #     await ctx.send(embed=create_success_embed("System Operational", f"✅ Bot is active.\n📶 Latency: `{lat}ms`\n🦅 {self.bot.user.name} is listening.", user=ctx.author, bot_user=self.bot.user))

    @commands.hybrid_command(name="status", hidden=True)
    async def status(self, ctx: commands.Context):
        """[Owner] Bot Statistics."""
        if not is_bot_owner(ctx.author.id):
             await ctx.send(embed=create_error_embed("No Permission", "Only owners can use this.", user=ctx.author, bot_user=self.bot.user))
             return
        
        # 1. Gather ID Lists
        member_ids = [str(m.id) for m in ctx.guild.members] if ctx.guild else ["0"]
        if not member_ids: member_ids = ["0"]
        
        db = SessionLocal()
        try:
             # Global Counts
             g_prem = db.query(UserProfile).filter_by(premium=True).count()
             g_nop = db.query(UserProfile).filter_by(no_prefix=True).count()
             
             # Local counts if in guild
             l_prem = 0
             l_nop = 0
             if ctx.guild:
                 l_prem = db.query(UserProfile).filter(UserProfile.user_id.in_(member_ids), UserProfile.premium == True).count()
                 l_nop = db.query(UserProfile).filter(UserProfile.user_id.in_(member_ids), UserProfile.no_prefix == True).count()
             
        except Exception as e:
             await ctx.send(embed=create_error_embed(None, f"Database error: {e}", user=ctx.author), delete_after=10)
             return
        finally:
             db.close()
             
        active_vc = len(self.bot.voice_clients)
        server_count = len(self.bot.guilds)
        total_users = sum(g.member_count or 0 for g in self.bot.guilds)
        
        embed = create_embed(title="📊 Bot Statistics", user=ctx.author, bot_user=self.bot.user)
        
        if ctx.guild:
            embed.add_field(
                name=f"📍 This Server (**{ctx.guild.name}**)", 
                value=f"> **Premium Users:** `{l_prem}`\n> **No-Prefix Users:** `{l_nop}`", 
                inline=False
            )
            embed.add_field(name="\u200b", value="\u200b", inline=False)
        
        embed.add_field(
            name="🌍 Global Stats",
            value=(
                f"\n> **Servers:** `{server_count}`\n"
                f"> **Users:** `{total_users}`\n"
                f"> **Active VCs:** `{active_vc}`\n"
                f"> **Global Premium:** `{g_prem}`\n"
                f"> **Global No-Prefix:** `{g_nop}`"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed, delete_after=10)

    # ==========================================================================
    # 🎨 BOT CUSTOMIZATION
    # ==========================================================================

    @commands.hybrid_group(name="customize", aliases=["setbot", "botset"], invoke_without_command=True)
    async def customize_group(self, ctx: commands.Context):
        """[Premium] Customize the bot's profile and status (Server Owner Only)."""
        is_owner = is_bot_owner(ctx.author.id)
        is_srv_owner = ctx.guild and ctx.author.id == ctx.guild.owner_id
        has_premium = is_premium(ctx.author.id)

        if not (is_owner or (is_srv_owner and has_premium)):
             error_msg = "Only **Bot Owners** or **Premium Server Owners** can use this."
             if is_srv_owner and not has_premium:
                 error_msg = "Please upgrade to **Premium** to customize my profile! 💎"
             await ctx.send(embed=create_error_embed("No Permission", error_msg, user=ctx.author))
             return
        await ctx.send_help(ctx.command)

    def _check_cust_perm(self, ctx):
        """Internal helper for customization permissions."""
        if is_bot_owner(ctx.author.id): return True
        if ctx.guild and ctx.author.id == ctx.guild.owner_id and is_premium(ctx.author.id): return True
        return False

    @customize_group.command(name="nick")
    async def customize_nick(self, ctx: commands.Context, *, name: str = None):
        """Change the bot's nickname in this server."""
        if not self._check_cust_perm(ctx): return
        try:
            await ctx.guild.me.edit(nick=name)
            await ctx.send(embed=create_success_embed("Nickname Updated", f"✅ Set nickname to `{name or 'Default'}`", user=ctx.author))
        except Exception as e:
            await ctx.send(embed=create_error_embed("Failed", f"I couldn't change my nickname: {e}", user=ctx.author))

    @customize_group.command(name="avatar")
    async def customize_avatar(self, ctx: commands.Context, url: str = None):
        """Change the bot's global avatar (URL or Attachment)."""
        if not self._check_cust_perm(ctx): return
        
        avatar_url = url or (ctx.message.attachments[0].url if ctx.message.attachments else None)
        if not avatar_url:
            return await ctx.send(embed=create_error_embed("Missing Info", "Please provide a URL or attach an image.", user=ctx.author))
            
        msg = await ctx.send(embed=create_embed(None, "Updating avatar...", user=ctx.author))
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(avatar_url) as resp:
                    if resp.status != 200:
                        return await msg.edit(embed=create_error_embed("Failed", "Could not download the image.", user=ctx.author))
                    data = await resp.read()
                    await self.bot.user.edit(avatar=data)
            await msg.edit(embed=create_success_embed("Avatar Updated", "✅ Global avatar has been updated.", user=ctx.author))
        except Exception as e:
            await msg.edit(embed=create_error_embed("Failed", f"Error: {e}", user=ctx.author))

    @customize_group.command(name="activity")
    async def customize_activity(self, ctx: commands.Context, type: str, *, status: str):
        """Set bot activity (streaming, watching, listening, playing, reset)."""
        if not self._check_cust_perm(ctx): return
        
        type = type.lower()
        if type == "reset":
            ConfigManager.set_global_config("custom_activity_name", "")
            await self.bot.change_presence(activity=None)
            return await ctx.send(embed=create_success_embed("Activity Reset", "✅ Activity has been reset to default.", user=ctx.author))

        # Store in config to persist across restarts and status_loop
        ConfigManager.set_global_config("custom_activity_name", status)
        ConfigManager.set_global_config("custom_activity_type", type)
        
        activity = None
        if type == "streaming":
            activity = discord.Streaming(name=status, url="https://twitch.tv/discord")
        elif type == "watching":
            activity = discord.Activity(type=discord.ActivityType.watching, name=status)
        elif type == "listening":
            activity = discord.Activity(type=discord.ActivityType.listening, name=status)
        elif type == "playing":
            activity = discord.Game(name=status)
        else:
            return await ctx.send(embed=create_error_embed("Invalid Type", "Use: `streaming`, `watching`, `listening`, `playing`, or `reset`.", user=ctx.author))

        await self.bot.change_presence(activity=activity)
        await ctx.send(embed=create_success_embed("Activity Updated", f"✅ Set activity to **{type.title()}**: `{status}`", user=ctx.author))

    @customize_group.command(name="bio")
    async def customize_bio(self, ctx: commands.Context, *, text: str):
        """Update the bot's 'About Me' description."""
        if not self._check_cust_perm(ctx): return
        try:
            await self.bot.http.edit_application(data={"description": text})
            await ctx.send(embed=create_success_embed("Bio Updated", "✅ Bot 'About Me' updated successfully.", user=ctx.author))
        except Exception as e:
            await ctx.send(embed=create_error_embed("Failed", f"Could not update bio: {e}\nTry updating in the Developer Portal.", user=ctx.author))

    @customize_group.command(name="banner")
    async def customize_banner(self, ctx: commands.Context, url: str = None):
        """Update the bot's profile banner."""
        if not self._check_cust_perm(ctx): return
        
        banner_url = url or (ctx.message.attachments[0].url if ctx.message.attachments else None)
        if not banner_url:
            return await ctx.send(embed=create_error_embed("Missing Info", "Please provide a URL or attach an image.", user=ctx.author))

        msg = await ctx.send(embed=create_embed(None, "Attempting to update banner...", user=ctx.author))
        try:
            import aiohttp
            import base64
            async with aiohttp.ClientSession() as session:
                async with session.get(banner_url) as resp:
                    if resp.status != 200:
                        return await msg.edit(embed=create_error_embed("Failed", "Could not download image.", user=ctx.author))
                    data = await resp.read()
                    
            mime = resp.content_type
            b64_data = base64.b64encode(data).decode('utf-8')
            data_uri = f"data:{mime};base64,{b64_data}"
            
            await self.bot.http.edit_application(data={"banner": data_uri})
            await msg.edit(embed=create_success_embed("Banner Updated", "✅ Bot banner updated successfully.", user=ctx.author))
        except Exception as e:
            await msg.edit(embed=create_error_embed("Failed", f"Error: {e}\nNote: Banner updates via API may be restricted.", user=ctx.author))

    @commands.hybrid_command(name="reloadconfig", hidden=True)
    async def reload_config(self, ctx: commands.Context):
        """[Owner] Reload configuration from disk."""
        if not is_bot_owner(ctx.author.id):
             await ctx.send(embed=create_error_embed("No Permission", "Only owners can use this.", user=ctx.author, bot_user=self.bot.user))
             return
        
        ConfigManager.reload()
        await ctx.send(embed=create_success_embed(None, "Config reloaded from disk.", user=ctx.author), delete_after=10)

    @commands.hybrid_command(name="sethq", hidden=True)
    async def set_hq(self, ctx: commands.Context, server_id: str):
        """[Owner] Set the HQ Support Server ID."""
        if not is_bot_owner(ctx.author.id): return
        
        if ConfigManager.set_global_config("hq_server_id", server_id):
            await ctx.send(embed=create_success_embed(None, f"HQ Server ID set to `{server_id}`", user=ctx.author), delete_after=10)
        else:
            await ctx.send(embed=create_error_embed(None, "Failed to update global config.", user=ctx.author), delete_after=10)

    @commands.hybrid_command(name="setowner", hidden=True)
    async def set_owner(self, ctx: commands.Context, user_id: str):
        """[Owner] Change bot owner (Be careful!)."""
        if not is_bot_owner(ctx.author.id): return
        
        if ConfigManager.set_global_config("owner_id", user_id):
            await ctx.send(embed=create_success_embed(None, f"Bot Owner ID set to `{user_id}`", user=ctx.author), delete_after=10)
        else:
            await ctx.send(embed=create_error_embed(None, "Failed to update global config.", user=ctx.author), delete_after=10)

    @commands.hybrid_command(name="setglobalprefix", hidden=True)
    async def set_global_prefix(self, ctx: commands.Context, prefix: str):
        """[Owner] Set the global default prefix."""
        if not is_bot_owner(ctx.author.id): return
        
        if ConfigManager.set_global_config("global_prefix", prefix):
            await ctx.send(embed=create_success_embed(None, f"Default prefix set to `{prefix}`", user=ctx.author), delete_after=10)
        else:
            await ctx.send(embed=create_error_embed(None, "Failed to update global config.", user=ctx.author), delete_after=10)

    @commands.command(name="saavn", hidden=True)
    async def toggle_saavn(self, ctx: commands.Context, state: str = None):
        """[Owner] Globally enable/disable JioSaavn integration."""
        if not is_bot_owner(ctx.author.id): return
        
        import config.settings as settings
        if state:
             settings.JIOSAAVN_GLOBAL_ENABLED = state.lower() in ["on", "enable", "true"]
        else:
             settings.JIOSAAVN_GLOBAL_ENABLED = not settings.JIOSAAVN_GLOBAL_ENABLED
             
        status = "On ✅" if settings.JIOSAAVN_GLOBAL_ENABLED else "Off ❌"
        await ctx.send(embed=create_success_embed(None, f"JioSaavn is now **{status}**.", user=ctx.author), delete_after=10)

    @commands.command(name="spotify", hidden=True)
    async def toggle_spotify(self, ctx: commands.Context, state: str = None):
        """[Owner] Globally enable/disable Spotify integration."""
        if not is_bot_owner(ctx.author.id): return
        
        import config.settings as settings
        if state:
             settings.SPOTIFY_ENABLED = state.lower() in ["on", "enable", "true"]
        else:
             settings.SPOTIFY_ENABLED = not getattr(settings, "SPOTIFY_ENABLED", True)
             
        status = "On ✅" if settings.SPOTIFY_ENABLED else "Off ❌"
        await ctx.send(embed=create_success_embed(None, f"Spotify is now **{status}**.", user=ctx.author), delete_after=10)

    # ==========================================================================
    # 🔓 NO-PREFIX MANAGEMENT
    # ==========================================================================

    @commands.hybrid_group(name="noprefix", aliases=["npref", "npre","np"], invoke_without_command=True)
    async def np_group(self, ctx: commands.Context):
        """[Owner] Manage No-Prefix users."""
        logger.info(f"Owner {ctx.author.id} invoked np_group")
        if not is_bot_owner(ctx.author.id):
             await ctx.send(embed=create_error_embed(None, "Only bot owners can manage no-prefix access.", user=ctx.author), delete_after=10)
             return
        await ctx.send_help(ctx.command)

    @np_group.command(name="add")
    async def np_add(self, ctx: commands.Context, user: discord.User, duration: str = "30d"):
        """Add user to No-Prefix list (e.g. 1y, 30mi, 0=Lifetime)."""
        if not is_bot_owner(ctx.author.id):
            await ctx.send(embed=create_error_embed("No Permission", "Only **Bot Owners** can use this.", user=ctx.author))
            return
        
        parsed = parse_duration(duration)
        expires_at = None
        
        if parsed:
            expires_at = ist_now() + parsed
            
        db = SessionLocal()
        try:
            profile = db.query(UserProfile).filter_by(user_id=str(user.id)).first()
            if not profile:
                profile = UserProfile(user_id=str(user.id))
                db.add(profile)
            
            profile.no_prefix = True
            profile.np_expires_at = expires_at
            db.commit()

            dur_str = f"**{duration}**" if parsed else "**Lifetime**"
            
            # Premium Success Embed
            embed = create_success_embed(
                "No-Prefix Added",
                f"✅ {arrow} Access granted to {user.mention}\n⏳ {arrow} Duration: {dur_str}",
                user=ctx.author,
                bot_user=self.bot.user
            )
            await ctx.send(embed=embed, delete_after=10)

            try:
                # Refined NP Activation DM
                dm_embed = create_embed(
                    title="Access Unlocked 🔓",
                    description=(
                        f"Hi {user.name}, we've turned on **No-Prefix** mode for you!\n"
                        f"You can now use all my commands without any prefix for {dur_str}.\n\n"
                        "Have fun! 🎵"
                    ),
                    bot_user=self.bot.user
                )
                await user.send(embed=dm_embed)
            except: pass
        except Exception as e:
            db.rollback()
            await ctx.send(embed=create_error_embed(None, f"Error: {e}", user=ctx.author), delete_after=10)
        finally: db.close()

    @np_group.command(name="remove", aliases=["rm"])
    async def np_remove(self, ctx: commands.Context, user: discord.User):
        """Remove user from No-Prefix list."""
        if not is_bot_owner(ctx.author.id):
            await ctx.send(embed=create_error_embed("No Permission", "Only **Bot Owners** can use this.", user=ctx.author))
            return
        
        db = SessionLocal()
        try:
            profile = db.query(UserProfile).filter_by(user_id=str(user.id)).first()
            if profile:
                profile.no_prefix = False
                profile.np_expires_at = None
                db.commit()
            
            embed = create_success_embed(
                "No-Prefix Removed",
                f"❌ {arrow} Revoked access from {user.mention}",
                user=ctx.author,
                bot_user=self.bot.user
            )
            await ctx.send(embed=embed, delete_after=10)

            try:
                # Refined NP Removal DM
                dm_embed = create_info_embed(
                    "Access Ended",
                    (
                        f"Hi {user.name}, your independent 'No-Prefix' access has ended.\n"
                        "You can still use me with my regular prefix. Have a great day! 🎵"
                    ),
                    bot_user=self.bot.user
                )
                await user.send(embed=dm_embed)
            except: pass
        except Exception as e:
            db.rollback()
            await ctx.send(embed=create_error_embed(None, f"Error: {e}", user=ctx.author), delete_after=10)
        finally: db.close()

    @np_group.command(name="list")
    async def np_list(self, ctx: commands.Context):
        """List all No-Prefix users."""
        if not is_bot_owner(ctx.author.id):
            await ctx.send(embed=create_error_embed("No Permission", "Only **Bot Owners** can use this.", user=ctx.author))
            return
        
        db = SessionLocal()
        try:
            users = db.query(UserProfile).filter_by(no_prefix=True).all()
            if not users:
                await ctx.send(embed=create_info_embed(None, "No users found in the list.", bot_user=self.bot.user), delete_after=10)
                return
                
            lines = [f"• <@{u.user_id}> (`{u.user_id}`)" for u in users]
            embed = create_embed("🔓 No-Prefix Users", "\n".join(lines), user=ctx.author, bot_user=self.bot.user)
            embed.set_footer(text=f"{self.bot.user.name} | Total: {len(users)}", icon_url=self.bot.user.display_avatar.url)
            await ctx.send(embed=embed, delete_after=10)
        finally: db.close()

    # ==========================================================================
    # 💎 SUBSCRIPTION MANAGEMENT
    # ==========================================================================

    @commands.hybrid_group(name="pm", aliases=["premiummanage"], invoke_without_command=True)
    async def pm_group(self, ctx: commands.Context):
        """[Owner] Manage Premium users."""
        logger.info(f"Owner {ctx.author.id} invoked pm_group")
        if not is_bot_owner(ctx.author.id):
             await ctx.send(embed=create_error_embed(None, "Only bot owners can manage premium.", user=ctx.author), delete_after=10)
             return
        await ctx.send_help(ctx.command)

    @pm_group.command(name="add")
    async def pm_add(self, ctx: commands.Context, user: discord.User, duration: str = "30d"):
        """Grant premium to a user (e.g. 1y, 30mi, 0=Lifetime)."""
        logger.info(f"Owner {ctx.author.id} invoked pm_add for {user.id}")
        if not is_bot_owner(ctx.author.id):
            await ctx.send(embed=create_error_embed(None, "Only bot owners can manage premium.", user=ctx.author), delete_after=10)
            return
        
        parsed = parse_duration(duration)
        now = ist_now()
        
        db = SessionLocal()
        try:
            profile = db.query(UserProfile).filter_by(user_id=str(user.id)).first()
            if not profile:
                profile = UserProfile(user_id=str(user.id))
                db.add(profile)
            
            profile.premium = True
            profile.no_prefix = True # Premium users auto-get No-Prefix
            
            if parsed:
                if profile.premium_expires_at and profile.premium_expires_at > now:
                    profile.premium_expires_at = profile.premium_expires_at + parsed
                else:
                    profile.premium_expires_at = now + parsed
                
                # Link NP expiry to Premium expiry
                profile.np_expires_at = profile.premium_expires_at
                duration_str = f"**{duration}**"
            else:
                profile.premium_expires_at = None # Lifetime
                profile.np_expires_at = None # Lifetime
                duration_str = "**Lifetime**"
            
            db.commit()
            logger.info(f"Premium Persistence: Committed {user.id} as Premium until {profile.premium_expires_at}")
            
            # Audit Log
            await self.bot.log_bot_event("premium_add", f"Added {duration_str} to {user.id}", {"moderator": ctx.author.id, "duration": duration})

            try:
                # Refined Activation DM
                embed = create_embed(
                    title="Welcome to the Family! 💎",
                    description=(
                        f"Hi {user.name}, we've just activated your **Meloxi Premium** for {duration_str}.\n"
                        "We're really glad to have you with us!\n\n"
                        "**Your Perks:**\n"
                        "• Use commands with No-Prefix\n"
                        "• Best music quality\n"
                        "• Exclusive profile badge\n\n"
                        "Enjoy the music! 🎵"
                    ),
                    bot_user=self.bot.user
                )
                await user.send(embed=embed)
            except: pass
            
            # Refined Command Response
            embed = create_success_embed(
                "Premium Added",
                f"💎 {arrow} Granted to {user.mention}\n⏳ {arrow} Duration: {duration_str}",
                user=ctx.author,
                bot_user=self.bot.user
            )
            await ctx.send(embed=embed, delete_after=10)
            
        except Exception as e:
            db.rollback()
            logger.error(f"PM Add Error: {e}")
            await ctx.send(embed=create_error_embed(None, f"Error: {e}", user=ctx.author), delete_after=10)
        finally: db.close()

    @pm_group.command(name="remove", aliases=["rm"])
    async def pm_remove(self, ctx: commands.Context, user: discord.User):
        """Revoke premium from a user."""
        if not is_bot_owner(ctx.author.id):
            await ctx.send(embed=create_error_embed(None, "Only bot owners can manage premium.", user=ctx.author), delete_after=10)
            return
        
        db = SessionLocal()
        try:
            profile = db.query(UserProfile).filter_by(user_id=str(user.id)).first()
            if profile:
                profile.premium = False
                profile.premium_expires_at = None
                
                # Optional: Handle linked NP. 
                # If they had independent NP, removing premium shouldn't kill it.
                # But requested logic says: "Adding Premium: premium=True, no_prefix=True..."
                # Usually we remove NP if it was linked.
                profile.no_prefix = False
                profile.np_expires_at = None
                
                db.commit()

            embed = create_success_embed(
                "Premium Removed",
                f"❌ {arrow} Revoked from {user.mention}",
                user=ctx.author,
                bot_user=self.bot.user
            )
            await ctx.send(embed=embed, delete_after=10)
            
            try:
                # Refined Removal DM
                embed = create_info_embed(
                    "Premium Ended",
                    (
                        f"Hi {user.name}, your premium time has ended.\n"
                        "Your perks are now turned off, but you can always renew using `/buy`.\n\n"
                        "Thanks for supporting us! 🎵"
                    ),
                    bot_user=self.bot.user
                )
                await user.send(embed=embed)
            except: pass
            
        except Exception as e:
            db.rollback()
            await ctx.send(embed=create_error_embed(None, f"Error: {e}", user=ctx.author), delete_after=10)
        finally: db.close()

    @pm_group.command(name="list")
    async def pm_list(self, ctx: commands.Context):
        """List all Premium users."""
        if not is_bot_owner(ctx.author.id):
            await ctx.send(embed=create_error_embed(None, "Only bot owners can manage premium.", user=ctx.author), delete_after=10)
            return
        
        logger.info(f"Owner {ctx.author.id} listing premium users...")
        
        db = SessionLocal()
        try:
            users = db.query(UserProfile).filter_by(premium=True).all()
            if not users:
                await ctx.send(embed=create_info_embed("Empty", "I couldn't find any premium users.", bot_user=self.bot.user))
                return
                
            lines = []
            for p in users:
                exp = p.premium_expires_at.strftime("%d %b %Y") if p.premium_expires_at else "Infinite"
                lines.append(f"• <@{p.user_id}> (`{p.user_id}`) — Ends: `{exp}`")
                      
            embed = create_embed("💎 Premium Users", "\n".join(lines), user=ctx.author, bot_user=self.bot.user)
            embed.set_footer(text=f"{self.bot.user.name} | Total: {len(users)}", icon_url=self.bot.user.display_avatar.url)
            await ctx.send(embed=embed, delete_after=10)
        finally: db.close()

    @commands.command(name="rpsync")
    @commands.is_owner()
    async def rpsync(self, ctx: commands.Context):
        """[Owner] Force Sync Razorpay Subscriptions."""
        msg = await ctx.send(embed=create_info_embed(None, "Getting data from Razorpay...", bot_user=self.bot.user), delete_after=10)
        count = await self.sub_manager.sync_all_subscriptions()
        await msg.edit(embed=create_success_embed(None, f"Successfully synced **{count}** users.", user=ctx.author))

    @commands.command(name="dbrepair", aliases=["dbfix"], hidden=True)
    @commands.is_owner()
    async def dbrepair(self, ctx: commands.Context):
        """[Owner] Fix missing DB columns."""
        from sqlalchemy import text, inspect
        db = SessionLocal()
        try:
            inspector = inspect(db.get_bind())
            columns = [c["name"] for c in inspector.get_columns("user_profiles")]
            
            status_msg = f"**Current Columns:** {', '.join(columns)}\n\n"
            
            # 1. Check/Add manual/renamed np_expires_at
            if "np_expires_at" not in columns:
                try:
                    db.execute(text("ALTER TABLE user_profiles ADD COLUMN np_expires_at DATETIME"))
                    db.commit()
                    status_msg += "✅ Added `np_expires_at`.\n"
                except Exception as e:
                    db.rollback()
                    status_msg += f"⚠️ `np_expires_at` error: {e}\n"
            else:
                status_msg += "✅ `np_expires_at` exists.\n"

            await ctx.send(embed=create_success_embed(None, status_msg, user=ctx.author), delete_after=10)
        except Exception as e:
            await ctx.send(embed=create_error_embed(None, f"Repair failed: {e}", user=ctx.author), delete_after=10)
        finally: db.close()

async def setup(bot):
    await bot.add_cog(Owner(bot))

