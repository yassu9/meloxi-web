"""
Main Entry Point for Meloxi.
Handles initialization, event listeners, and global command registration.
"""

# ==============================================================================
# 📥 IMPORTS
# ==============================================================================

# Suppress Google Generative AI FutureWarnings
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# Standard Library
import os
import sys
import asyncio
import re
from typing import Literal

# Ensure macOS SSL certs work for aiohttp/discord.py
try:
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
except Exception:
    pass

# Discord
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

# Local Modules
from config.settings import BOT_TOKEN, OWNER_ID, HQ_SERVER_ID, COLOR_PRIMARY, DEFAULT_PREFIX
from database.db import init_db, SessionLocal
from utils.logger import logger, log_to_database
from utils.config_manager import ConfigManager
from utils.permissions import is_bot_owner, is_no_prefix, is_premium
from utils.noprefix import NoPrefixManager
from ui.embeds import create_embed, create_success_embed, create_error_embed, create_warning_embed
from music.music import get_player
from premium.razorpay_webhook import WebhookServer

# Load Env
load_dotenv()

# ==============================================================================
# 🤖 BOT CLASS
# ==============================================================================

class MeloxiBot(commands.Bot):
    """
    Custom Bot Class.
    Manages startup, database connections, and event loops.
    """
    
    def __init__(self):
        # Intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.members = True
        
        super().__init__(
            command_prefix=self.get_prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True
        )
    

    async def get_prefix(self, message):
        """Determine prefix: Mention, UserBypass, or Guild/Global Default."""
        # 1. Start with .env Default
        defaults = [DEFAULT_PREFIX, DEFAULT_PREFIX.upper()]
        
        # Dynamic Prefixes
        if self.user:
            defaults.extend([f"{self.user.name} ", f"{self.user.name.upper()} "])
            # Purge legacy references to allow full dynamic rebranding
        
        # 2. Check Guild Custom Prefix
        if message.guild:
            custom = ConfigManager.get_prefix(str(message.guild.id))
            if custom and custom not in defaults:
                defaults.append(custom)

        # 3. User Bypass (No Prefix for Premium/NoPrefix roles)
        # We always wrap in when_mentioned_or to support @Bot commands
        if message.author and (is_no_prefix(message.author.id) or is_premium(message.author.id)):
            return commands.when_mentioned_or(*defaults, "")(self, message)
             
        return commands.when_mentioned_or(*defaults)(self, message)
    
    async def setup_hook(self):
        """Global Setup: DB, Cogs, Sync."""
        # 1. Database
        init_db()
        logger.info("Database initialized.")
        
        # 2. Load Cogs
        cogs = [
            "music.music", 
            "premium.premium", 
            "admin.admin", 
            "general.profile",
            "general.helpmenu",
            "general.xp",
            "general.serverinfo",
            "general.userinfo",
            "general.botinfo",
            "general.invited",
            "owner.owner"
        ]
        
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"✅ Loaded extension: {cog}")
            except Exception as e:
                logger.error(f"❌ Failed to load extension {cog}: {e}")
        
        # 3. Webhook Server
        try:
            self.webhook_server = WebhookServer(self)
            await self.webhook_server.start()
        except Exception as e:
            logger.error(f"❌ Webhook Server Start Failed: {e}")

        # 4. Sync Commands
        try:
            synced = await self.tree.sync()
            logger.info(f"✅ Synced {len(synced)} commands.")
        except Exception as e:
            logger.warning(f"Cmd Sync failed: {e}")
        
        # 5. Global Interaction Check
        self.tree.interaction_check = self.global_interaction_check
        
        # 6. Finalize
        await self.log_bot_event("system", "Bot started", {"version": "1.0.0"})
        self.bg_task = self.loop.create_task(self.status_loop())
    
    async def status_loop(self):
        """Cycle Status Messages (Simplified)."""
        await self.wait_until_ready()
        while not self.is_closed():
              try:
                  # 1. Check for Custom Global Activity
                  custom_name = ConfigManager.get_global_config("custom_activity_name")
                  if custom_name:
                      custom_type = ConfigManager.get_global_config("custom_activity_type", "streaming")
                      activity = None
                      
                      if custom_type == "streaming":
                          activity = discord.Streaming(name=custom_name, url="https://twitch.tv/discord")
                      elif custom_type == "watching":
                          activity = discord.Activity(type=discord.ActivityType.watching, name=custom_name)
                      elif custom_type == "listening":
                          activity = discord.Activity(type=discord.ActivityType.listening, name=custom_name)
                      elif custom_type == "playing":
                          activity = discord.Game(name=custom_name)
                      
                      if activity:
                          await self.change_presence(activity=activity)
                          await asyncio.sleep(600)
                          continue

                  # 2. Default Status
                  guild_count = len(self.guilds)
                  member_count = sum(g.member_count for g in self.guilds if g.member_count)
                  name_to_use = self.user.name if self.user else "MELOXI"
                  status_text = f"{name_to_use} | {DEFAULT_PREFIX}help | {guild_count} Server | {member_count} Member"
                  # Using Streaming for the Purple dot as requested
                  await self.change_presence(activity=discord.Streaming(name=status_text, url="https://twitch.tv/discord"))
                  await asyncio.sleep(600) 
              except Exception as e:
                   logger.error(f"Status Loop Error: {e}")
                   await asyncio.sleep(60)

    async def is_channel_locked(self, message_or_int) -> bool:
        """Centralized check for channel locking. Returns True if command should be BLOCKED."""
        if not message_or_int.guild: return False
        
        # 1. Get Config
        config = ConfigManager.get_server_config(str(message_or_int.guild.id))
        if not config.music_channel_id: return False
        
        # 2. Check Channel
        channel_id = str(message_or_int.channel.id)
        is_request_channel = config.request_channel_id and channel_id == config.request_channel_id
        
        # 3. Bypass Logic: Owner
        user = message_or_int.author if hasattr(message_or_int, 'author') else message_or_int.user
        is_owner = is_bot_owner(user.id)
        
        logger.info(f"Lock Eval: User={user.id} ({user.name}), Channel={channel_id}, Target={config.music_channel_id}, IsOwner={is_owner}")
        
        if channel_id == config.music_channel_id or is_request_channel: return False
        
        if is_owner: return False
        
        # 4. Filter: Only lock MUSIC commands
        music_cogs = ["Music", "Mood", "AutoDJ", "Suggestions"]
        
        if isinstance(message_or_int, discord.Interaction):
            if not message_or_int.command: return False
            cog_name = getattr(message_or_int.command.binding, "qualified_name", "") if hasattr(message_or_int.command, "binding") else ""
            logger.info(f"Lock Check (Slash): Cmd={message_or_int.command.name}, Cog={cog_name}, Blocked={cog_name in music_cogs}")
            if cog_name not in music_cogs: return False
        else:
            ctx = await self.get_context(message_or_int)
            if not ctx.command: return False
            cog_name = ctx.cog.qualified_name if ctx.cog else ""
            logger.info(f"Lock Check (Prefix): Cmd={ctx.command.name}, Cog={cog_name}, Blocked={cog_name in music_cogs}")
            if cog_name not in music_cogs: return False

        return True

    async def global_interaction_check(self, interaction: discord.Interaction) -> bool:
        """Global check for all slash commands."""
        if await self.is_channel_locked(interaction):
            config = ConfigManager.get_server_config(str(interaction.guild.id))
            ch = self.get_channel(int(config.music_channel_id))
            c_name = f"**{ch.mention if ch else config.music_channel_id}**"
            await interaction.response.send_message(embed=create_error_embed(None, f"Please use this channel: {c_name}", user=interaction.user), ephemeral=True)
            return False
        return True

    async def on_ready(self):
        """Bot Ready Event."""
        logger.info(f"Logged in as: {self.user} (ID: {self.user.id})")

    async def on_command(self, ctx: commands.Context):
        """Global command entry point."""
        logger.info(f"Executing command: {ctx.command.qualified_name} | User: {ctx.author}")

    async def on_message(self, message: discord.Message):
        """Handle Messages & Mentions."""
        if message.author.bot: return
        
        # [LOG FILTER] Only log chat if it's in a Request Channel or a valid command
        config = ConfigManager.get_server_config(str(message.guild.id)) if message.guild else None
        is_request_ch = config and config.request_channel_id and str(message.channel.id) == config.request_channel_id
        
        if is_request_ch:
            logger.info(f"Incoming Message: {message.author} | Content: {message.content}")

        # 1. Handle JUST a mention (Show Prefix)
        clean = message.content.strip()
        if re.fullmatch(rf"<@!?{self.user.id}>", clean):
            prefix = config.prefix if config else DEFAULT_PREFIX
            await message.channel.send(f"My prefix is: `{prefix}`")
            return
        
        # Channel Locking Check
        if await self.is_channel_locked(message):
            ch = self.get_channel(int(config.music_channel_id))
            c_name = f"**{ch.mention if ch else config.music_channel_id}**"
            await message.channel.send(embed=create_error_embed(None, f"Please use this channel: {c_name}", user=message.author), delete_after=10)
            return
        
        # IMPORTANT: Process commands AFTER all checks
        ctx = await self.get_context(message)
        if ctx.valid or is_request_ch:
             logger.info(f"Command Context: Valid={ctx.valid} | Prefix='{ctx.prefix}' | Command={ctx.command}")
        await self.process_commands(message)
        
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Global Slash Command Error Handling."""
        if isinstance(error, app_commands.CommandOnCooldown):
            return await interaction.response.send_message(embed=create_warning_embed(None, f"Take a breath! Try again in **{error.retry_after:.1f}s**.", user=interaction.user), ephemeral=True)
            
        if isinstance(error, app_commands.MissingPermissions):
            return await interaction.response.send_message(embed=create_error_embed(None, f"You need these permissions: **{', '.join(error.missing_permissions)}**", user=interaction.user), ephemeral=True)

        logger.error(f"Slash Command Error: {error}", exc_info=error)
        
        # Generic Fail
        try:
             msg = "An unexpected error occurred."
             if interaction.response.is_done():
                  await interaction.followup.send(embed=create_error_embed(None, msg, user=interaction.user), ephemeral=True)
             else:
                  await interaction.response.send_message(embed=create_error_embed(None, "Something went wrong.", user=interaction.user), ephemeral=True)
        except: pass

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Global Error Handling with Human Touch."""
        if hasattr(ctx.command, "on_error"):
            # Command has a local error handler (e.g., @purge.error). Let it handle things.
            return

        # Unwrap the error if it originated from a slash command execution
        error = getattr(error, 'original', error)

        if isinstance(error, commands.CommandNotFound):
            # Fuzzy Logic
            import difflib
            cmd = ctx.invoked_with
            all_cmds = [c.name for c in self.commands if not c.hidden]
            match = difflib.get_close_matches(cmd, all_cmds, n=1, cutoff=0.6)
            
            if match:
                await ctx.send(embed=create_warning_embed(None, f"Did you mean `{ctx.prefix}{match[0]}`?", user=ctx.author), delete_after=10)
            return
        
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=create_warning_embed(
                None, f"I need more info for this command!\nTry: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`", user=ctx.author
            ), delete_after=10)
            return
        
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(embed=create_warning_embed(
                None, f"Take a breath! You can use this again in **{error.retry_after:.1f}s**.", user=ctx.author
            ), delete_after=10)
            return
        
        if isinstance(error, commands.MissingPermissions):
             await ctx.send(embed=create_error_embed(
                None, f"You need these permissions: **{', '.join(error.missing_permissions)}**", user=ctx.author
            ), delete_after=10)
             return
        
        if isinstance(error, commands.BadLiteralArgument):
             await ctx.send(embed=create_warning_embed(
                None, f"Please choose one of: `{', '.join(error.literals)}`", user=ctx.author
            ), delete_after=10)
             return
             
        # Parameter Conversion Errors (e.g., invalid channel name "me", invalid user "test")
        if isinstance(error, commands.ChannelNotFound):
            await ctx.send(embed=create_error_embed(None, f"I couldn't find the channel: `{error.argument}`. Please tag a valid text channel.", user=ctx.author), delete_after=10)
            return
            
        if isinstance(error, commands.UserNotFound) or isinstance(error, commands.MemberNotFound):
            await ctx.send(embed=create_error_embed(None, f"I couldn't find the user: `{error.argument}`. Please tag a valid member or provide their ID.", user=ctx.author), delete_after=10)
            return
            
        if isinstance(error, commands.RoleNotFound):
            await ctx.send(embed=create_error_embed(None, f"I couldn't find the role: `{error.argument}`. Please tag a valid role.", user=ctx.author), delete_after=10)
            return
            
        if isinstance(error, commands.BadArgument):
            # Generic fallback for invalid inputs (e.g., 'purge auto' -> invalid integer)
            await ctx.send(embed=create_error_embed(None, f"Invalid value provided. Please check the command usage: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`", user=ctx.author), delete_after=10)
            return

        logger.error(f"Command Error: {error}", exc_info=error)
        await self.log_bot_event("error", f"Cmd Error: {error}", {"command": ctx.command.name if ctx.command else "?"})
        
        # Catch-all: Ensure no raw tracebacks go to Discord
        try:
            # Only send error message if it's not a noise error
            await ctx.send(embed=create_error_embed(None, "Something went wrong while doing that.", user=ctx.author), delete_after=10)
        except:
            pass
    
    async def log_bot_event(self, log_type: str, message: str, metadata: dict = None):
        """Log to Database."""
        try:
            db = SessionLocal()
            await log_to_database(db, log_type, message, metadata)
            db.close()
        except Exception:
            pass
    
    async def close(self):
        """Shutdown Cleanup."""
        logger.info("Stopping the bot...")
        for vc in self.voice_clients:
            try: await vc.disconnect()
            except: pass
        await super().close()

# ==============================================================================
#  MAIN
# ==============================================================================

def main():
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN is missing!")
        sys.exit(1)
    
    bot = MeloxiBot()
    bot.run(BOT_TOKEN)

if __name__ == "__main__":
    main()
