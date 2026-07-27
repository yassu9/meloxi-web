"""
Admin Cog for Meloxi.
Server management, configuration, and diagnostics.
"""

# ==============================================================================
# 📥 IMPORTS
# ==============================================================================

import asyncio
import platform
import subprocess
from datetime import datetime, timedelta, timezone
from sqlalchemy import text, inspect

import discord
from discord.ext import commands
from discord import app_commands

from ui.embeds import create_success_embed, create_error_embed, create_embed
from utils.config_manager import ConfigManager
from utils.permissions import can_manage_server, is_bot_owner, is_no_prefix
from utils.logger import logger
from config.settings import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, COLOR_ACCENT, COLOR_ERROR
from database.db import SessionLocal
from config.emojis import arrow
from database.models import ServerConfig

# ==============================================================================
# 🛠️ ADMIN COG
# ==============================================================================

class Admin(commands.Cog):
    """Admin commands."""
    
    def __init__(self, bot):
        self.bot = bot

    # ==========================================================================
    # ⚙️ SETTINGS
    # ==========================================================================
    
    @commands.hybrid_command(name="setchannel", aliases=["setch"])
    @app_commands.describe(channel="Text channel for music commands")
    async def set_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Lock music commands to specific channel."""
        if not can_manage_server(ctx.author):
            await ctx.send(embed=create_error_embed(None, "Only admins can use this.", user=ctx.author), delete_after=10)
            return
        
        target = channel or ctx.channel
        db = SessionLocal()
        try:
            config = db.query(ServerConfig).filter_by(server_id=str(ctx.guild.id)).first()
            if not config:
                 config = ServerConfig(server_id=str(ctx.guild.id))
                 db.add(config)
            config.music_channel_id = str(target.id)
            db.commit()
            
            guild_icon = ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None
            await ctx.send(embed=create_success_embed(None, f"I will only work in {target.mention} now.", user=ctx.author, guild_icon_url=guild_icon), delete_after=10)
        except Exception as e:
            db.rollback()
            await ctx.send(embed=create_error_embed(None, f"Error: {e}", user=ctx.author), delete_after=10)
        finally: db.close()
    
    @commands.hybrid_command(name="setvoice", aliases=["setvc"])
    async def set_voice(self, ctx: commands.Context, channel: discord.VoiceChannel = None):
        """Set fixed voice channel."""
        if not can_manage_server(ctx.author):
            await ctx.send(embed=create_error_embed(None, "Only admins can use this.", user=ctx.author), delete_after=10)
            return
        
        if not channel:
             await ctx.send(embed=create_error_embed(None, "Please specify a voice channel.", user=ctx.author), delete_after=10)
             return
        
        db = SessionLocal()
        try:
            config = db.query(ServerConfig).filter_by(server_id=str(ctx.guild.id)).first()
            if not config:
                 config = ServerConfig(server_id=str(ctx.guild.id))
                 db.add(config)
            config.voice_channel_id = str(channel.id)
            db.commit()
            
            # 🛡️ 24/7 Join Enforcement
            if config.auto_247:
                try:
                    if ctx.voice_client: await ctx.voice_client.move_to(channel)
                    else: await channel.connect(timeout=20, reconnect=True)
                except Exception as e:
                    logger.warning(f"Failed to join 24/7 VC in setvoice: {e}")

            guild_icon = ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None
            await ctx.send(embed=create_success_embed(None, f"I will always stay in {channel.mention}.", user=ctx.author, guild_icon_url=guild_icon), delete_after=10)
        finally: db.close()
    
    @commands.hybrid_command(name="247")
    async def toggle_247(self, ctx: commands.Context):
        """Toggle 24/7 Mode."""
        if not can_manage_server(ctx.author):
            await ctx.send(embed=create_error_embed(None, "Only admins can use this.", user=ctx.author), delete_after=10)
            return
        
        db = SessionLocal()
        try:
            config = db.query(ServerConfig).filter_by(server_id=str(ctx.guild.id)).first()
            if not config:
                 config = ServerConfig(server_id=str(ctx.guild.id))
                 db.add(config)
            config.auto_247 = not config.auto_247
            db.commit()
            state = "Enabled" if config.auto_247 else "Disabled"
            guild_icon = ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None
            await ctx.send(embed=create_success_embed("24/7 Mode", f"The mode is now **{state}**", user=ctx.author, bot_user=self.bot.user, guild_icon_url=guild_icon))
        finally: db.close()
    
    @commands.hybrid_command(name="prefix")
    async def set_prefix(self, ctx: commands.Context, new_prefix: str = None):
        """Set/View custom prefix."""
        if not can_manage_server(ctx.author):
             await ctx.send(embed=create_error_embed(None, "Only admins can use this.", user=ctx.author), delete_after=10)
             return
        
        guild_icon = ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None
        
        if new_prefix:
            if ConfigManager.set_prefix(str(ctx.guild.id), new_prefix):
                await ctx.send(embed=create_success_embed(None, f"New prefix: `{new_prefix}`", user=ctx.author), delete_after=10)
        else:
            curr = ConfigManager.get_prefix(str(ctx.guild.id))
            await ctx.send(embed=create_success_embed(None, f"Current: `{curr}`", user=ctx.author), delete_after=10)

    @commands.hybrid_command(name="setup", aliases=["musicsetup", "setupmusic"])
    @app_commands.describe(channel="Channel to use for song requests")
    async def setup(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Initialize the persistent Song Request interface in a channel."""
        if not can_manage_server(ctx.author):
             await ctx.send(embed=create_error_embed(None, "Only admins can use this.", user=ctx.author), delete_after=10)
             return
             
        target = channel or ctx.channel
        try: await target.purge(limit=100)
        except: pass

        db = SessionLocal()
        try:
            config = db.query(ServerConfig).filter_by(server_id=str(ctx.guild.id)).first()
            if not config:
                config = ServerConfig(server_id=str(ctx.guild.id))
                db.add(config)
            config.request_channel_id = str(target.id)
            config.request_message_id = None 
            db.commit()
            
            music_cog = self.bot.get_cog("Music")
            if music_cog: await music_cog._update_request_channel(ctx.guild.id)
            
            guild_icon = ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None
            await ctx.send(embed=create_success_embed(None, f"The interface is ready in {target.mention}", user=ctx.author), delete_after=10)
        finally: db.close()

    @commands.hybrid_command(name="refresh_request_channel", aliases=["refreshch", "rch"])
    async def refresh_request_channel(self, ctx: commands.Context):
        """Force refresh the Song Request channel UI."""
        if not can_manage_server(ctx.author):
             await ctx.send(embed=create_error_embed("No Permission", "Only admins can use this.", user=ctx.author, bot_user=self.bot.user), delete_after=5)
             return
        
        config = ConfigManager.get_server_config(str(ctx.guild.id))
        if not config.request_channel_id:
            await ctx.send(embed=create_error_embed("Wait", "You need to use `/setup` first.", user=ctx.author, bot_user=self.bot.user), delete_after=10)
            return
        
        target = self.bot.get_channel(int(config.request_channel_id))
        try:
            if target: await target.purge(limit=100)
            db = SessionLocal()
            try:
                cfg = db.query(ServerConfig).filter_by(server_id=str(ctx.guild.id)).first()
                cfg.request_message_id = None
                db.commit()
            finally: db.close()

            music_cog = self.bot.get_cog("Music")
            if music_cog: await music_cog._update_request_channel(ctx.guild.id)
            await ctx.send(embed=create_success_embed(None, "The interface has been updated.", user=ctx.author), delete_after=10)
        except Exception as e:
            await ctx.send(embed=create_error_embed(None, f"Error: {e}", user=ctx.author), delete_after=10)

    # ==========================================================================
    # 🛡️ MODERATION
    # ==========================================================================
    
    @commands.hybrid_command(name="purge")
    async def purge(self, ctx: commands.Context, limit: int = 20):
        """Bulk delete messages."""
        if not (can_manage_server(ctx.author) or is_bot_owner(ctx.author.id)):
             await ctx.send(embed=create_error_embed(None, "Admin access required.", user=ctx.author), delete_after=10)
             return
        
        limit = min(limit, 100)
        try: await ctx.message.delete()
        except: pass
        
        delt = await ctx.channel.purge(limit=limit)
        guild_icon = ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None
        msg = await ctx.send(embed=create_success_embed(None, f"Successfully deleted {len(delt)} messages.", user=ctx.author, bot_user=self.bot.user, guild_icon_url=guild_icon), delete_after=10)
        await asyncio.sleep(5)
        try: await msg.delete()
        except: pass

    @purge.error
    async def purge_error(self, ctx: commands.Context, error: commands.CommandError):
        from discord.ext.commands import BadArgument
        if isinstance(error, BadArgument):
             await ctx.send(embed=create_error_embed(None, "Invalid limit. Please provide a number (e.g., `purge 20`).", user=ctx.author), delete_after=10)




    @commands.hybrid_group(name="features", aliases=["fe", "feature", "featur", "sfe"], invoke_without_command=True)
    async def fe_group(self, ctx: commands.Context, name: str = None, state: str = None):
        """Manage server features. Use `fe list` to see all."""
        # If no arguments, show list (backward compatibility and convenience)
        if not name:
             await self.fe_list(ctx)
             return
             
        # If arguments provided but no subcommand, treat as toggle (legacy support)
        
        # Smart Swap: Support "fe on all" -> "fe all on"
        if name.lower() in ["on", "off", "enable", "disable"] and state:
             await self.fe_toggle(ctx, state, name)
             return

        await self.fe_toggle(ctx, name, state)

    @fe_group.command(name="list")
    async def fe_list(self, ctx: commands.Context):
        """List all available features and their status."""
        from utils.features import FeatureManager
        desc = []
        for key, label in FeatureManager.AVAILABLE_FEATURES.items():
            # Ghost Feature: Strictly Hidden from UI (Backend Only)
            if key == "jiosaavn": continue
            
            is_on = FeatureManager.is_enabled(str(ctx.guild.id), key)
            status = "On" if is_on else "Off"
            desc.append(f"> {arrow} **{label}**: `{status}`")
        
        guild_icon = ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None
        embed = create_embed("Server Features", "\n".join(desc), user=ctx.author, bot_user=self.bot.user, guild_icon_url=guild_icon, show_footer=True)
        await ctx.send(embed=embed)

    @fe_group.command(name="toggle")
    async def fe_toggle(self, ctx: commands.Context, name: str, state: str = None):
        """Toggle a specific feature (e.g. `{ctx.prefix}fe toggle autodj on`)."""
        from utils.features import FeatureManager
        
        if not can_manage_server(ctx.author):
            await ctx.send(embed=create_error_embed(None, "Admins only.", user=ctx.author), delete_after=10)
            return
            
        arg1 = name.lower()
        arg2 = state.lower() if state else ""
        
        # BULK TOGGLE
        guild_icon = ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None
        
        # BULK TOGGLE
        if arg1 == "all":
             if not arg2: # Require state for safety
                 await ctx.send(embed=create_error_embed(None, f"Use `on` or `off` with `all`.", user=ctx.author), delete_after=10)
                 return
                 
             new_state = arg2 not in ["off", "disable"]
             for k in FeatureManager.AVAILABLE_FEATURES:
                  # Ghost Feature: Skip in bulk toggle
                  if k == "jiosaavn": continue
                  FeatureManager.set_enabled(str(ctx.guild.id), k, new_state)
             txt = "Enabled" if new_state else "Disabled"
             await ctx.send(embed=create_success_embed(None, f"All features are now **{txt}**.", user=ctx.author), delete_after=10)
             return

        # SINGLE FEATURE
        if arg1 not in FeatureManager.AVAILABLE_FEATURES:
             await ctx.send(embed=create_error_embed(None, "Unknown feature specified.", user=ctx.author), delete_after=10)
             return

        # Restrict Owner Features
        if arg1 == "jiosaavn" and not is_bot_owner(ctx.author.id):
             await ctx.send(embed=create_error_embed(None, "Unknown feature specified.", user=ctx.author), delete_after=10)
             return
             
        if not arg2 or arg2 not in ["on", "off", "enable", "disable"]:
             current = FeatureManager.is_enabled(str(ctx.guild.id), arg1)
             status = "✅ Enabled" if current else "❌ Disabled"
             await ctx.send(embed=create_embed(FeatureManager.AVAILABLE_FEATURES[arg1], f"Current Status: **{status}**\nUse `on` or `off` to change.", user=ctx.author, bot_user=self.bot.user, guild_icon_url=guild_icon))
             return
             
        new_state = arg2 in ["on", "enable"]
        FeatureManager.set_enabled(str(ctx.guild.id), arg1, new_state)
        
        action = "Enabled" if new_state else "Disabled"
        await ctx.send(embed=create_success_embed(None, f"**{FeatureManager.AVAILABLE_FEATURES[arg1]}** is now **{action}**.", user=ctx.author), delete_after=10)



    # ==========================================================================
    # ☢️ NUKE
    # ==========================================================================

    @commands.hybrid_command(name="nuke")
    async def nuke(self, ctx: commands.Context):
        """Clone and recreate channel to clear history."""
        if not (can_manage_server(ctx.author) or is_bot_owner(ctx.author.id)):
             await ctx.send(embed=create_error_embed(None, "Admins only.", user=ctx.author), delete_after=10)
             return

        channel = ctx.channel
        pos = channel.position
        if not isinstance(channel, discord.TextChannel):
            await ctx.send(embed=create_error_embed(None, "Only text channels can be nuked.", user=ctx.author), delete_after=10)
            return

        # Confirmation? No, nuke usually instant or rapid.
        # Clone
        try:
            new_channel = await channel.clone(reason=f"Nuked by {ctx.author.name}")
            await new_channel.edit(position=pos)
            
            # Send Embed
            guild_icon = ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None
            embed = create_embed(
                title="Channel Nuked", 
                description=f"> {arrow} **Action by**: {ctx.author.mention}\n> {arrow} **Time**: <t:{int(datetime.now().timestamp())}:R>", 
                color=COLOR_ERROR, 
                user=ctx.author, 
                bot_user=self.bot.user,
                guild_icon_url=guild_icon,
                show_footer=True
            )
            await new_channel.send(embed=embed)
            await channel.delete(reason=f"Nuked by {ctx.author.name}")
            
        except Exception as e:
            await ctx.send(embed=create_error_embed(None, f"Nuke failed: {e}", user=ctx.author), delete_after=10)

    # ==========================================================================
    # ⚙️ FULL CONFIGURATION
    # ==========================================================================

    @commands.hybrid_command(name="settings", aliases=["conf", "config"])
    async def settings(self, ctx: commands.Context):
        """View Server Configuration Dashboard."""
        if not can_manage_server(ctx.author):
             await ctx.send(embed=create_error_embed(None, "Admins only.", user=ctx.author), delete_after=10)
             return

        guild_icon = ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None
        
        # Fetch Data
        prefix = ConfigManager.get_prefix(str(ctx.guild.id))
        from utils.features import FeatureManager
        
        db = SessionLocal()
        try:
            cfg = db.query(ServerConfig).filter_by(server_id=str(ctx.guild.id)).first()
            
            # Defaults if no config
            music_ch = f"<#{cfg.music_channel_id}>" if cfg and cfg.music_channel_id else "Not Set"
            voice_ch = f"<#{cfg.voice_channel_id}>" if cfg and cfg.voice_channel_id else "Not Set"
            req_ch = f"<#{cfg.request_channel_id}>" if cfg and cfg.request_channel_id else "Not Set"
            auto_247 = "On" if cfg and cfg.auto_247 else "Off"
            
        finally: db.close()

        # Features List
        feats = []
        for key, label in FeatureManager.AVAILABLE_FEATURES.items():
            # Ghost Feature: Strictly Hidden
            if key == "jiosaavn": continue
            
            is_on = FeatureManager.is_enabled(str(ctx.guild.id), key)
            icon = "✅" if is_on else "❌"
            feats.append(f"{icon} **{label}**")
        
        from config.emojis import section, arrow
        
        embed = create_embed(
            title="Server Settings", 
            user=ctx.author, 
            bot_user=self.bot.user,
            guild_icon_url=guild_icon,
            show_footer=True
        )
        
        embed.add_field(name=f"{section} Core", value=f"> {arrow} **Prefix**: `{prefix}`\n> {arrow} **24/7 Mode**: {auto_247}", inline=True)
        embed.add_field(name=f"{section} Channels", value=f"> {arrow} **Music**: {music_ch}\n> {arrow} **Voice**: {voice_ch}\n> {arrow} **Request**: {req_ch}", inline=True)
        embed.add_field(name=f"{section} Features", value="\n".join([f"> {arrow} {f}" for f in feats]), inline=False)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Admin(bot))
