"""
Consolidated Music Controller for Meloxi.
Contains Music, Mood, AutoDJ, and Suggestions Cogs.
"""

# ==============================================================================
# 📥 IMPORTS
# ==============================================================================

import asyncio
import math
import re
import discord
import random
from typing import Optional, Literal
from discord.ext import commands
from discord import app_commands

# Local Modules
from music.player import MusicPlayer
from utils.logger import logger
from utils.config_manager import ConfigManager
from utils.features import FeatureManager
from utils.permissions import can_manage_server, is_premium, is_bot_owner
from general.xp import add_music_xp, get_user_level
import config.settings as settings # Fix NameError
from ui.embeds import (
    create_success_embed, create_error_embed, create_warning_embed,
    create_now_playing_embed, create_queue_embed, create_song_added_embed,
    create_info_embed, create_embed
)

from config.emojis import (
    EMOJI_PLAYING, EMOJI_PAUSED, EMOJI_LOOP, EMOJI_LOOP_ONE, 
    EMOJI_NEXT, EMOJI_PREVIOUS, EMOJI_STOP_ACTION, EMOJI_SHUFFLE,
    EMOJI_VOLUME_HIGH, EMOJI_VOLUME_LOW, EMOJI_VOLUME_MUTE,
    EMOJI_NOTE, EMOJI_MIC, EMOJI_CD, EMOJI_TIME,
    LABEL_PLAY, LABEL_PAUSE, LABEL_SKIP, LABEL_STOP, LABEL_LOOP, LABEL_SHUFFLE,
    arrow, section
)
from config.settings import COLOR_PRIMARY, COLOR_ACCENT

# ==============================================================================
# 📦 GLOBAL STATE
# ==============================================================================

players: dict[int, MusicPlayer] = {}
now_playing_messages: dict[int, discord.Message] = {}
now_playing_views: dict[int, discord.ui.View] = {}

# ==============================================================================
# 🛠️ HELPER FUNCTIONS
# ==============================================================================

def get_player(guild_id: int) -> MusicPlayer:
    """Get or create MusicPlayer for guild."""
    if guild_id not in players:
        players[guild_id] = MusicPlayer(guild_id)
    return players[guild_id]

# Inject get_player into views to avoid circular imports
import music.views as views
from config.emojis import CD, EMOJI_CD, EMOJI_SEARCH
views._get_player_func = get_player

async def update_voice_channel_activity(bot, guild: discord.Guild, song_title: Optional[str] = None):
    """Updates the Voice Channel's status to show "🎧 Listening to <Song>"."""
    ANIMATED_CD = "<a:cd:1468293207770140672>"
    try:
        voice_client = discord.utils.get(bot.voice_clients, guild=guild)
        if voice_client and voice_client.channel:
            vc = voice_client.channel
            if isinstance(vc, discord.VoiceChannel):
                if song_title:
                     new_status = f" {ANIMATED_CD} Playing: {song_title[:80]}"
                else:
                     new_status = "Queue Empty | /play [song] 🎵"
                
                current_status = getattr(vc, 'status', "") or ""
                if current_status != new_status:
                    try:
                        perms = vc.permissions_for(guild.me)
                        if perms.manage_channels or perms.administrator:
                             await vc.edit(status=new_status)
                    except: pass

        # if song_title:
        #     await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f"{song_title[:95]}"))
    except Exception as e:
        logger.error(f"Failed to update VC activity: {e}")

    except Exception as e:
        logger.error(f"Failed to update VC activity: {e}")

# ==============================================================================
# 🎵 MUSIC COG
# ==============================================================================

class Music(commands.Cog):
    async def _get_join_lock(self, guild_id: int) -> asyncio.Lock:
        """Get or create a connection lock for a guild."""
        if guild_id not in self._join_locks:
            self._join_locks[guild_id] = asyncio.Lock()
        return self._join_locks[guild_id]

    def __init__(self, bot):
        self.bot = bot
        self.progress_tasks = {}
        self.request_cooldown = commands.CooldownMapping.from_cooldown(1, 4.0, commands.BucketType.user)
        self._join_locks: dict[int, asyncio.Lock] = {}
        self._synced = False # Re-run guard for on_ready

    def cog_unload(self):
        for task in self.progress_tasks.values():
            if task and not task.done(): task.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        """Cleanup and refresh request channels on startup and auto-join 24/7 channels."""
        # 🛡️ RACE CONDITION GUARD
        if getattr(self, '_synced', False): return
        self._synced = True

        await self.bot.wait_until_ready()

        # Phase 0: Warmup
        # Give shards time to settle and cache to populate
        logger.info("🎵 [Startup] Initializing Music System (10s warmup)...")
        await asyncio.sleep(10)
        
        # Phase 1: Join 24/7 Channels (Priority)
        # We do this FIRST without any text-channel noise to minimize gateway strain
        logger.info("🎵 [Phase 1] Joining 24/7 channels...")
        for guild in self.bot.guilds:
            try:
                config = ConfigManager.get_server_config(str(guild.id))
                if config.auto_247 and config.voice_channel_id:
                    vc = guild.get_channel(int(config.voice_channel_id))
                    if vc:
                        # 🧟 ZOMBIE CLEANUP
                        # If discord thinks we are connected but we have no valid session
                        if guild.voice_client:
                            try: await guild.voice_client.disconnect(force=True)
                            except: pass
                            await asyncio.sleep(1)

                        try:
                            # 🧩 Stagger connections significantly (4s)
                            await asyncio.sleep(4.0) 
                            
                            vc_client = await vc.connect(timeout=30, reconnect=True, self_deaf=True)
                            
                            # ⚓ SYNC PLAYER REFERENCE
                            player = get_player(guild.id)
                            player.voice_client = vc_client
                            
                            logger.info(f"✅ [Phase 1] Auto-Joined 24/7: {guild.name}")
                        except Exception as e:
                            logger.warning(f"❌ [Phase 1] Failed Join {guild.name}: {e}")
            except Exception as e:
                logger.error(f"Error in Join Phase for {guild.name}: {e}")

        # Phase 2: UI & Request Channel Sync
        # Only start cleaning up AFTER all voices are (hopefully) connected
        logger.info("🎵 [Phase 2] Syncing Request Channels & UI...")
        for guild in self.bot.guilds:
            try:
                config = ConfigManager.get_server_config(str(guild.id))
                if not config.request_channel_id: continue
                
                channel = self.bot.get_channel(int(config.request_channel_id))
                if not channel: continue
                
                # Stagger UI updates too to prevent text rate limits
                await asyncio.sleep(1.0)

                # Clean Channel
                if channel.permissions_for(guild.me).manage_messages:
                    try:
                        await channel.purge(limit=100, check=lambda m: m.author != self.bot.user or m.id != int(config.request_message_id or 0))
                    except: pass
                
                # Refresh Embed
                await self._update_request_channel(guild.id)
                logger.debug(f"✅ [Phase 2] Sync Complete: {guild.name}")
            except Exception as e:
                logger.error(f"Error in Sync Phase for {guild.name}: {e}")

        logger.info("🎵 [Startup] Music System Fully Operational.")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Listen for internal voice state changes to keep Player synced."""
        if member.id != self.bot.user.id: return

        # ⚓ Anchor: Keep MusicPlayer.voice_client in lock-step with Guild.voice_client
        guild = member.guild
        player = get_player(guild.id)
        
        # If we disconnected, clear player reference
        if not after.channel:
            player.voice_client = None
            logger.debug(f"VC Sync: Cleared player voice reference for {guild.name}")
        else:
            # If we connected/moved, update player reference
            player.voice_client = guild.voice_client
            logger.debug(f"VC Sync: Updated player voice reference for {guild.name}")

    async def _update_request_channel(self, guild_id: int):
        try:
            config = ConfigManager.get_server_config(str(guild_id))
            if not config.request_channel_id: return
            channel = self.bot.get_channel(int(config.request_channel_id))
            if not channel: return
            player = get_player(guild_id)
            
            if player.current:
                song = player.current
                total = int(song.get("duration", 0))
                is_live = song.get("is_live", False)
                if is_live:
                    duration_str = "LIVE"
                else:
                    duration_str = f"{total // 60}:{total % 60:02d}" if total > 0 else "0:00"
                requester_id = song.get("requester_id")
                requester = self.bot.get_user(int(requester_id)) if requester_id else None
                progress_pct = player.get_progress()
                progress_seconds = progress_pct * total if total > 0 else 0
                
                listeners = len([m for m in player.voice_client.channel.members if not m.bot]) if player.voice_client and player.voice_client.channel else 0
                
                embed = create_now_playing_embed(
                    song_title=song.get('title', 'Unknown'),
                    duration=duration_str,
                    requester=requester,
                    loop=player.loop,
                    progress=progress_seconds,
                    thumbnail=song.get("thumbnail"),
                    artist=song.get('artist'),
                    bot_user=self.bot.user,
                    listeners=listeners,
                    source=song.get('source'),
                    status_override="Paused" if player.is_paused else None,
                    volume=player.volume,
                    guild_icon=channel.guild.icon.url if channel.guild.icon else None,
                    queue_len=len(player.queue)
                )
            else:
                from config.emojis import section, arrow, EMOJI_NOTE
                bot_name = self.bot.user.name.upper() if self.bot.user else "MUSIC"
                embed = discord.Embed(title=f"{bot_name} Music Station", description=f"{section} **Ready to play your music!**\n\n> {arrow} Join a voice channel\n> {arrow} Type any song name here\n> {arrow} Enjoy high-fidelity audio", color=settings.COLOR_PRIMARY)
                embed.set_image(url="https://i.imgur.com/K1vXpE0.png")
            
            view = views.RequestChannelView(self.bot, guild_id)
            view.update_buttons(player)
            if config.request_message_id:
                try:
                    msg = await channel.fetch_message(int(config.request_message_id))
                    await msg.edit(embed=embed, view=view)
                except:
                    msg = await channel.send(embed=embed, view=view)
                    self._save_request_msg_id(guild_id, msg.id)
            else:
                msg = await channel.send(embed=embed, view=view)
                self._save_request_msg_id(guild_id, msg.id)
        except Exception as e: logger.error(f"Request Channel Update Error: {e}")

    def _save_request_msg_id(self, guild_id, msg_id):
        from database.db import SessionLocal
        from database.models import ServerConfig
        db = SessionLocal()
        try:
            cfg = db.query(ServerConfig).filter_by(server_id=str(guild_id)).first()
            if cfg: cfg.request_message_id = str(msg_id); db.commit()
        finally: db.close()

    async def _start_progress_loop(self, ctx, player):
        guild_id = ctx.guild.id
        try:
            while player.current and (player.is_playing or player.is_paused):
                await asyncio.sleep(15) # Increased from 5s to 15s to prevent Discord 429 Rate Limits
                if not player.current: break
                try:
                    await self._update_request_channel(guild_id)
                    if guild_id in now_playing_messages:
                        await self._update_now_playing(ctx, player.current, None, guild_id=guild_id, is_update=True)
                except: pass
        except asyncio.CancelledError: pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild: return
        config = ConfigManager.get_server_config(str(message.guild.id))
        
        if not config.request_channel_id or str(message.channel.id) != config.request_channel_id: return
        
        # Exempt Owner from Rate Limits
        from utils.permissions import is_bot_owner
        if not is_bot_owner(message.author.id):
             bucket = self.request_cooldown.get_bucket(message)
             if bucket.update_rate_limit():
                 try: await message.delete(); await message.channel.send(f"Slow down!", delete_after=3)
                 except: pass
                 return
        
        # Debug Log for Owner Issues
        # if is_bot_owner(message.author.id):
        #      logger.info(f"Owner Message in Req Channel: '{message.content}'")

        # Fix for NoPrefix Users (Owner):
        # get_prefix returns "" for them, causing startswith("") to be always True.
        # We must ignore the empty string so the listener processes the text as a song query.
        raw_prefixes = await self.bot.get_prefix(message)
        if isinstance(raw_prefixes, str): raw_prefixes = [raw_prefixes]
        
        # Only check against ACTUAL prefixes (ignore empty strings)
        valid_prefixes = [p for p in raw_prefixes if p and str(p).strip()]
        
        if valid_prefixes and message.content.startswith(tuple(valid_prefixes)): return
        query = message.content.strip()
        if not query: return
        
        try: await message.delete()
        except: pass
        
        if not message.author.voice:
            await message.channel.send(embed=create_error_embed("Join Voice", "You must be in VC.", user=message.author), delete_after=5)
            return
            
        ctx = await self.bot.get_context(message)
        
        status_msg = await message.channel.send(f"{EMOJI_SEARCH} Searching: `{query}`...")
        try: await self.play(ctx, query=query)
        finally:
            if status_msg:
                try: await status_msg.delete()
                except: pass

    async def _update_now_playing(self, ctx: Optional[commands.Context], song: dict, requester: discord.User = None, *, guild_id: int = None, send_new: bool = False, is_update: bool = False):
        if not guild_id: guild_id = ctx.guild.id if ctx else None
        
        # 🛡️ STABILITY GUARD: If no song provided, abort to prevent AttributeError
        if not song: return

        config = ConfigManager.get_server_config(str(guild_id))
        if config.request_channel_id:
            if send_new:
                 self.bot.dispatch("track_start", guild_id, song)
                 guild = self.bot.get_guild(guild_id) or (ctx.guild if ctx else None)
                 if guild: await update_voice_channel_activity(self.bot, guild, song.get('title'))
                 self.bot.loop.create_task(self._hydrate_suggestions(guild_id, song))
            return
        player = get_player(guild_id)
        total = int(song.get("duration", 0))
        duration_str = f"{total // 60}:{total % 60:02d}" if total > 0 else "LIVE"
        embed = create_now_playing_embed(
            song_title=song.get("title", "Unknown"), duration=duration_str, requester=requester,
            loop=player.loop, progress=player.get_progress()*total, thumbnail=song.get("thumbnail"),
            album=song.get("album") or song.get("series"), artist=song.get("artist") or song.get("uploader"),
            bot_user=self.bot.user, score=song.get('_quality_score', 0),
            brain_mode=True, listeners=len([m for m in player.voice_client.channel.members if not m.bot]) if player.voice_client and player.voice_client.channel else 0,
            status_override="Paused" if player.is_paused else ("Looping" if player.loop else "Playing"), source=song.get('source_display') or song.get('source')
        )
        view = now_playing_views.get(guild_id) if not send_new else views.NowPlayingView(self.bot, guild_id)
        if not view: view = views.NowPlayingView(self.bot, guild_id)
        view.update_buttons(player)
        if send_new:
            if guild_id in self.progress_tasks: self.progress_tasks[guild_id].cancel()
            if guild_id in now_playing_messages:
                try: await now_playing_messages[guild_id].delete()
                except: pass
            msg = await ctx.send(embed=embed, view=view)
            now_playing_messages[guild_id], now_playing_views[guild_id] = msg, view
            self.progress_tasks[guild_id] = self.bot.loop.create_task(self._start_progress_loop(ctx, player))
            self.bot.dispatch("track_start", guild_id, song)
            await update_voice_channel_activity(self.bot, ctx.guild, song.get('title'))
            self.bot.loop.create_task(self._hydrate_suggestions(guild_id, song))
        elif guild_id in now_playing_messages:
            try:
                msg = now_playing_messages[guild_id]
                await msg.edit(embed=embed, view=view)
                guild = ctx.guild if ctx else self.bot.get_guild(guild_id)
                if guild: await update_voice_channel_activity(self.bot, guild, song.get('title'))
            except discord.NotFound:
                if not is_update: await self._update_now_playing(ctx, song, requester, send_new=True)

    async def _hydrate_suggestions(self, guild_id: int, current_song: dict):
        await asyncio.sleep(2.5)
        player = get_player(guild_id)
        if not player.current or player.current.get("id") != current_song.get("id"): return
        final_suggestions = []
        seen_ids = set(player.played_ids)
        if current_song.get('id'): seen_ids.add(current_song['id'])
        related = player.current.get('related', [])
        for r in related[:5]:
            r_id = r.get('id')
            if r_id and r_id not in seen_ids:
                final_suggestions.append({'id': r_id, 'title': player._clean_title(r.get('title', 'Unknown')), 'uploader': r.get('uploader') or r.get('artist'), 'webpage_url': f"https://www.youtube.com/watch?v={r_id}"})
                seen_ids.add(r_id)
        if len(final_suggestions) < 8:
            try:
                from music.brain import brain
                brain_queries = await brain.get_suggestions(guild_id, current_song, limit=10)
                if brain_queries:
                    tasks = [player.search_youtube(q, limit=1, is_autodj=True) for q in brain_queries]
                    resolved_batches = await asyncio.gather(*tasks, return_exceptions=True)
                    for batch in resolved_batches:
                        if isinstance(batch, list) and batch:
                            track = batch[0]
                            if track.get('id') not in seen_ids:
                                final_suggestions.append(track); seen_ids.add(track.get('id'))
            except: pass
        if not final_suggestions:
             results = await player.search_youtube(f"{current_song.get('title', '')} Mix", limit=15, is_autodj=True)
             for s in results:
                 if s.get('id') not in seen_ids: final_suggestions.append(s); seen_ids.add(s.get('id'))
        if final_suggestions:
            player._last_suggestions = final_suggestions[:5]
            if guild_id in now_playing_views and guild_id in now_playing_messages:
                view = now_playing_views[guild_id]
                view.add_suggestions(player._last_suggestions)
                req_id = player.current.get('requester_id')
                requester = self.bot.get_user(int(req_id)) if req_id else None
                await self._update_now_playing(None, current_song, requester, guild_id=guild_id, is_update=True)

    async def _on_song_end(self, guild_id: int):
        player = get_player(guild_id)
        if player.force_stop: player.force_stop = False; return
        guild = self.bot.get_guild(guild_id)
        if not guild: return
        config = ConfigManager.get_server_config(str(guild_id))
        target_channel = guild.get_channel(int(config.music_channel_id)) if config.music_channel_id else (now_playing_messages[guild_id].channel if guild_id in now_playing_messages else None)
        if not target_channel:
            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).send_messages: target_channel = ch; break
        if not target_channel: return
        
        class FakeCtx:
             def __init__(self, g, c, b):
                 self.guild, self.channel, self.bot = g, c, b
                 self.author, self.send, self.defer = b.user, c.send, lambda: None
        ctx = FakeCtx(guild, target_channel, self.bot)
        await player.play_next()
        
        # Give AutoDJ a chance to kick in if queue was empty
        if not player.current:
            autodj = self.bot.get_cog("AutoDJ")
            if autodj: await autodj._check_and_auto_play(guild_id, player)

        if player.current:
            await update_voice_channel_activity(self.bot, guild, player.current.get("title"))
            if FeatureManager.is_enabled(str(guild_id), "xp_level_system"):
                req_id = player.current.get("requester_id")
                if req_id:
                    xp = 20 if is_premium(int(req_id)) else 10
                    if add_music_xp(int(req_id), xp):
                        user = self.bot.get_user(int(req_id))
                        if user:
                            lvl = get_user_level(user.id)
                            try: await ctx.send(embed=create_embed(title="Level Up", description=f"> {arrow} **{user.mention}** reached **Level {lvl}**!", color=COLOR_ACCENT))
                            except: pass
            if not config.request_channel_id:
                req_id = player.current.get("requester_id")
                await self._update_now_playing(ctx, player.current, self.bot.get_user(int(req_id)) if req_id else None, send_new=True)
            elif guild_id not in self.progress_tasks or self.progress_tasks[guild_id].done():
                self.progress_tasks[guild_id] = self.bot.loop.create_task(self._start_progress_loop(ctx, player))
            self.bot.dispatch("music_log", guild_id, "🎶 Started Playing", f"**{player.current.get('title')}**", COLOR_PRIMARY)
        else:
            await update_voice_channel_activity(self.bot, guild, None)
            if guild_id in now_playing_messages:
                try: await now_playing_messages[guild_id].delete()
                except: pass
                del now_playing_messages[guild_id]
            try: await ctx.send(embed=create_embed(title="Queue Ended", description=f"> {arrow} The playback has finished.", color=settings.COLOR_PRIMARY))
            except: pass
        await self._update_request_channel(guild_id)

    @commands.hybrid_command(name="play", aliases=["p"])
    async def play(self, ctx: commands.Context, *, query: str):
        # Defer immediately to prevent "Unknown interaction" on slow searches
        await ctx.defer()
        
        if not await self._ensure_voice(ctx): return
        player = get_player(ctx.guild.id)
        if query.lower() == "kill": return await self.stop(ctx)
        
        # 🧠 SMART MIX INTEGRATION
        # Attempt to resolve via Spotify/JioSaavn first
        try:
            from music.smart_search import smart_mix
            # Pass player for Fallback/Comparison capabilities
            smart_results = await smart_mix.resolve(query, ctx.author, player)
            
            if smart_results:
                # We got high-quality matches!
                added_count = 0
                first_song = None
                
                for song in smart_results:
                    song['requester_id'] = str(ctx.author.id)
                    player.add_to_queue(song)
                    if not first_song: first_song = song
                    added_count += 1
                
                # 🔒 MOOD LOCK LOGIC
                # If Smart Mix detected a mood (explicit 'mood:sad' or implicit), LOCK IT.
                detected_mood = smart_results[0].get('_detected_mood')
                if detected_mood:
                    player.active_mood = detected_mood
                    player.mood_lock_source = "user" # User initiated this mood
                    logger.info(f"Music: Mood LOCKED to '{detected_mood}' by User.")
                    # Optionally notify user? "Mood Locked: Sad 🔒" - maybe too verbose.
                    # Let's keep it silent but effective as requested ("No surprises").
                
                # ⚓ ANCHOR: Lock Genre/Language to this manual song
                if first_song:
                    player.anchor_metadata = first_song
                    logger.info(f"Music: Genre/Language Anchor Set -> '{first_song.get('title')}'")
                
                if not player.is_playing:
                    async def next_cb(): await self._on_song_end(ctx.guild.id)
                    player.next_callback, player.bot_loop = next_cb, self.bot.loop
                    await player.play_next()
                    # If single song, show now playing immediately
                    if added_count == 1:
                        await self._update_now_playing(ctx, player.current, ctx.author, send_new=True)
                    else:
                        await ctx.send(embed=create_song_added_embed(first_song, len(player.queue), ctx.author, self.bot.user, count=added_count))
                else:
                    # Enqueue Feedback
                    if added_count == 1:
                        await ctx.send(embed=create_song_added_embed(first_song, len(player.queue), ctx.author, self.bot.user), delete_after=10)
                    else:
                        await ctx.send(embed=create_success_embed("Playlist Added", f"✅ Added **{added_count}** songs from Smart Mix.", user=ctx.author), delete_after=10)
                
                await self._update_request_channel(ctx.guild.id)
                return # Skip YouTube Fallback
                
        except Exception as e:
            logger.error(f"Smart Mix Error: {e}")
            # Continue to fallback...
            
        # 🔻 LEGACY FALLBACK (YouTube)
        search_query = query if (query.startswith("http://") or query.startswith("https://")) else f"{query} song"
        try: results = await player.search_youtube(search_query, limit=1)
        except Exception as e: await ctx.send(embed=create_error_embed(None, "Something went wrong while searching.", user=ctx.author), delete_after=10); return
        if not results: await ctx.send(embed=create_error_embed(None, "I couldn't find that song.", user=ctx.author), delete_after=10); return
        
        song = results[0]
        song['requester_id'] = str(ctx.author.id)
        player.add_to_queue(song)
        if not player.is_playing:
            async def next_cb(): await self._on_song_end(ctx.guild.id)
            player.next_callback, player.bot_loop = next_cb, self.bot.loop
            await player.play_next()
            await self._update_now_playing(ctx, player.current, ctx.author, send_new=True)
        else:
            await ctx.send(embed=create_song_added_embed(song, len(player.queue), ctx.author, self.bot.user), delete_after=10)
        await self._update_request_channel(ctx.guild.id)

    async def _ensure_voice(self, ctx: commands.Context) -> bool:
        if not ctx.author.voice or not ctx.author.voice.channel:
             await ctx.send(embed=create_error_embed(None, "You need to join a voice channel first.", user=ctx.author), delete_after=10)
             return False
        
        # 🔒 Check Fixed Voice Channel (SetVC)
        config = ConfigManager.get_server_config(str(ctx.guild.id))
        if config.voice_channel_id:
            fixed_id = int(config.voice_channel_id)
            if ctx.author.voice.channel.id != fixed_id:
                vc = self.bot.get_channel(fixed_id)
                v_name = f"**{vc.name if vc else fixed_id}**"
                await ctx.send(embed=create_error_embed(None, f"I can only play in the: {v_name}", user=ctx.author), delete_after=10)
                return False

        player = get_player(ctx.guild.id)
        
        # 🔒 PER-GUILD CONNECTION LOCK: Prevents concurrent handshakes (Reduces 4006 session collisions)
        lock = await self._get_join_lock(ctx.guild.id)
        async with lock:
            if player.voice_client and not player.voice_client.is_connected():
                try: await player.voice_client.disconnect(force=True)
                except: pass
                player.voice_client = None

            if not player.voice_client:
                # Double check voice state after potential await
                if not ctx.author.voice or not ctx.author.voice.channel:
                    await ctx.send(embed=create_error_embed(None, "You need to join a voice channel first.", user=ctx.author), delete_after=10)
                    return False
                    
                perms = ctx.author.voice.channel.permissions_for(ctx.guild.me)
                if not perms.connect or not perms.speak:
                    await ctx.send(embed=create_error_embed(None, "I need `Connect` & `Speak` permissions for this channel.", user=ctx.author), delete_after=10)
                    return False

                guild_vc = ctx.guild.voice_client
                if guild_vc:
                    if guild_vc.channel and guild_vc.channel.id != ctx.author.voice.channel.id:
                        try:
                            await guild_vc.move_to(ctx.author.voice.channel)
                        except Exception as e:
                            logger.error(f"Failed to move VC: {e}")
                            try: await guild_vc.disconnect(force=True)
                            except: pass
                            guild_vc = None
                    if guild_vc: 
                        player.voice_client = guild_vc
                
                if not player.voice_client or not player.voice_client.is_connected():
                    try:
                        player.voice_client = await ctx.author.voice.channel.connect(self_deaf=True, timeout=15.0)
                    except asyncio.TimeoutError:
                        await ctx.send(embed=create_error_embed(None, "Handshake timeout. Please try again.", user=ctx.author), delete_after=10)
                        return False
                    except Exception as e:
                        logger.error(f"Join Error: {e}")
                        return False
            return True
        if player.voice_client and player.voice_client.channel and player.voice_client.channel.id != ctx.author.voice.channel.id:
             await ctx.send(embed=create_error_embed(None, "I'm already playing music in another channel.", user=ctx.author), delete_after=10)
             return False
        return True

    @commands.hybrid_command(name="stop")
    async def stop(self, ctx: commands.Context):
        player = get_player(ctx.guild.id)
        player.stop(); player.queue.clear()
        player.active_mood = None # [FIX] Clear mood loop on manual stop
        
        # 🛡️ 24/7 Check
        config = ConfigManager.get_server_config(str(ctx.guild.id))
        if player.voice_client:
            if not config.auto_247:
                await player.voice_client.disconnect()
                msg = "Stopped and disconnected."
            else:
                msg = "Stopped playback. (24/7 Active)"
        else:
            msg = "Stopped and cleared the queue."

        await ctx.send(embed=create_success_embed(None, msg, user=ctx.author), delete_after=10)
        await self._update_request_channel(ctx.guild.id)

    @commands.hybrid_command(name="skip", aliases=["s", "next"])
    async def skip(self, ctx: commands.Context):
        """Skip the current song."""
        if not await self._ensure_voice(ctx): return
        
        # 🛡️ Quality Gate: Ensure user is in the same VC
        player = get_player(ctx.guild.id)
        if not player.voice_client:
             await ctx.send(embed=create_error_embed(None, "I'm not in a voice channel.", user=ctx.author), delete_after=10)
             return

        await ctx.defer()
        await self._attempt_skip(ctx, ctx.guild.id, ctx.author)
        await ctx.send(embed=create_success_embed(None, "Skipped to the next song.", user=ctx.author), delete_after=10)

    async def _attempt_skip(self, interaction, guild_id, user):
        player = get_player(guild_id)
        # 🧠 Use Smart Skip for intelligent feedback recording
        if player.voice_client:
            await player.skip() 
        await self._update_request_channel(guild_id)

    @commands.hybrid_command(name="pause")
    async def pause(self, ctx: commands.Context):
        """Pause playback."""
        player = get_player(ctx.guild.id)
        if player.voice_client and player.voice_client.is_playing():
             player.pause()
             await ctx.send(embed=create_success_embed(None, "Playback paused.", user=ctx.author), delete_after=10)
             await self._update_request_channel(ctx.guild.id)
        else:
             await ctx.send(embed=create_error_embed(None, "I'm not playing anything right now.", user=ctx.author), delete_after=10)

    @commands.hybrid_command(name="resume")
    async def resume(self, ctx: commands.Context):
        """Resume playback."""
        player = get_player(ctx.guild.id)
        if player.voice_client and player.voice_client.is_paused():
             player.resume()
             await ctx.send(embed=create_success_embed(None, "Playback resumed.", user=ctx.author), delete_after=10)
             await self._update_request_channel(ctx.guild.id)
        else:
             await ctx.send(embed=create_error_embed(None, "The music is not paused.", user=ctx.author), delete_after=10)

    @commands.hybrid_command(name="queue", aliases=["q", "list"])
    async def queue(self, ctx: commands.Context):
        """View the song queue."""
        player = get_player(ctx.guild.id)
        guild_icon = ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None
        
        # We need a proper user/member context for footer
        embed = create_queue_embed(
            current_song=player.current, 
            queue_list=list(player.queue), 
            user=ctx.author, 
            member=ctx.guild.get_member(ctx.author.id), 
            bot_user=self.bot.user
        )
        # Manually fix footer icon if needed, or rely on create_queue_embed updates (we didn't update create_queue_embed to take guild_icon yet)
        # But wait, create_queue_embed uses _set_embed_footer default.
        # Let's fix create_queue_embed later if needed, or just set it here manually if possible.
        # Check embeds.py from memory: create_queue_embed calls create_embed.
        # I'll update it later or just patch it.
        # For now, let's just send it.
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="loop", aliases=["repeat"])
    async def loop(self, ctx: commands.Context):
        """Toggle loop mode."""
        player = get_player(ctx.guild.id)
        player.loop = not player.loop
        state = "Looping song" if player.loop else "Off"
        await ctx.send(embed=create_success_embed(None, f"Loop is now **{state}**.", user=ctx.author), delete_after=10)
        await self._update_request_channel(ctx.guild.id)

    @commands.hybrid_command(name="shuffle", aliases=["mix"])
    async def shuffle(self, ctx: commands.Context):
        """Shuffle the queue."""
        player = get_player(ctx.guild.id)
        if len(player.queue) < 1:
             await ctx.send(embed=create_error_embed(None, "The queue is empty.", user=ctx.author), delete_after=10)
             return
        random.shuffle(player.queue)
        await ctx.send(embed=create_success_embed(None, "Queue shuffled.", user=ctx.author), delete_after=10)
        await self._update_request_channel(ctx.guild.id)

    @commands.hybrid_command(name="volume", aliases=["vol", "v"])
    async def volume(self, ctx: commands.Context, level: int):
        """Set volume (0-100)."""
        if not 0 <= level <= 150:
             await ctx.send(embed=create_error_embed(None, "Volume must be between 0 and 150.", user=ctx.author), delete_after=10)
             return
        
        player = get_player(ctx.guild.id)
        player.volume = level / 100
        if player.voice_client and player.voice_client.source:
             player.voice_client.source.volume = player.volume
        
        await ctx.send(embed=create_success_embed(None, f"Volume set to **{level}%**.", user=ctx.author), delete_after=10)
        await self._update_request_channel(ctx.guild.id)

    @commands.hybrid_command(name="join", aliases=["j", "connect"])
    async def join(self, ctx: commands.Context):
        """Join your voice channel."""
        if await self._ensure_voice(ctx):
             await ctx.send(embed=create_success_embed(None, f"Joined {ctx.author.voice.channel.mention}.", user=ctx.author), delete_after=10)

    @commands.hybrid_command(name="leave", aliases=["dc", "disconnect"])
    async def leave(self, ctx: commands.Context):
        """Leave voice channel."""
        player = get_player(ctx.guild.id)
        if player.voice_client:
             await player.voice_client.disconnect()
             player.stop()
             await ctx.send(embed=create_success_embed(None, "Disconnected from the voice channel.", user=ctx.author), delete_after=10)
             await self._update_request_channel(ctx.guild.id)
        else:
             await ctx.send(embed=create_error_embed(None, "I'm not in a voice channel.", user=ctx.author), delete_after=10)

    @commands.hybrid_command(name="nowplaying", aliases=["now", "current"])
    async def nowplaying(self, ctx: commands.Context):
        """Show current song."""
        # [LOG FILTER] Only log command execution if it's in a Request Channel
        config = ConfigManager.get_server_config(str(ctx.guild.id)) if ctx.guild else None
        if config and config.request_channel_id and str(ctx.channel.id) == config.request_channel_id:
             logger.info(f"Executing command: {ctx.command.qualified_name} | User: {ctx.author}")
        
        player = get_player(ctx.guild.id)
        if not player.current:
             await ctx.send(embed=create_error_embed(None, "Nothing is playing right now.", user=ctx.author), delete_after=10)
             return
        await self._update_now_playing(ctx, player.current, None, send_new=True)

    @commands.hybrid_command(name="remove", aliases=["rm"])
    async def remove(self, ctx: commands.Context, index: int):
        """Remove a song from queue."""
        player = get_player(ctx.guild.id)
        if index < 1 or index > len(player.queue):
             await ctx.send(embed=create_error_embed(None, "That's not a valid song index.", user=ctx.author), delete_after=10)
             return
        
        removed = player.queue[index-1]
        del player.queue[index-1]
        await ctx.send(embed=create_success_embed(None, f"Removed **{removed.get('title')}**.", user=ctx.author), delete_after=10)
        await self._update_request_channel(ctx.guild.id)

    @commands.hybrid_command(name="clear", aliases=["cls"])
    async def clear(self, ctx: commands.Context):
        """Clear the queue."""
        player = get_player(ctx.guild.id)
        player.queue.clear()
        await ctx.send(embed=create_success_embed(None, "Cleared the entire queue.", user=ctx.author), delete_after=10)
        await self._update_request_channel(ctx.guild.id)

    @commands.hybrid_command(name="seek")
    async def seek(self, ctx: commands.Context, seconds: int):
        """Seek forward in seconds (Experimental)."""
        # Seek is hard with current simple ffmpeg setup without recreating source
        # For now, just say not supported or basic nudge
        await ctx.send(embed=create_info_embed(None, "Seek is not supported in this version.", user=ctx.author), delete_after=10)

# ==============================================================================
# 🎭 MOOD COG (Consolidated)
# ==============================================================================

class Mood(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name="sad")
    async def sad(self, ctx: commands.Context, era: str = None):
        """Play sad songs."""
        await self._play_mood(ctx, "sad", era)

    @commands.hybrid_command(name="romantic")
    async def romantic(self, ctx: commands.Context, era: str = None):
        """Play romantic songs."""
        await self._play_mood(ctx, "romantic", era)

    async def _play_mood(self, ctx: commands.Context, mood: str, era: str = None):
        music_cog = self.bot.get_cog("Music")
        if not music_cog or not await music_cog._ensure_voice(ctx): return
        
        await ctx.defer()
        player = get_player(ctx.guild.id)
        from music.ai import AIManager
        ai = AIManager()
        query = await ai.suggest_search_query(mood, era)
        results = await player.search_youtube(query, limit=5)
        if results:
            player.active_mood = mood # [FIX] Set active mood for Auto-DJ logic
            for s in results: 
                s['requester_id'] = str(ctx.author.id)
                player.add_to_queue(s)
            
            await ctx.send(embed=create_success_embed(None, f"Queued {len(results)} songs from **{mood.capitalize()}**.", user=ctx.author), delete_after=10)
            if not player.is_playing:
                async def next_cb(): await music_cog._on_song_end(ctx.guild.id)
                player.next_callback, player.bot_loop = next_cb, self.bot.loop
                await player.play_next()
                await music_cog._update_now_playing(ctx, player.current, ctx.author, send_new=True)

# ==============================================================================
# 🤖 AUTO-DJ COG (Consolidated)
# ==============================================================================

class AutoDJ(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def _check_and_auto_play(self, guild_id: int, player: MusicPlayer):
        # 🔒 RACE CONDITION PROTECTION
        if player.auto_dj_lock.locked(): return

        async with player.auto_dj_lock:
            # Re-check state inside lock
            if not FeatureManager.is_enabled(str(guild_id), "autodj"): return
            if player.is_playing or player.queue: return
            
            await self._auto_play_next(guild_id, player)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot: 
            # 🧹 SESSION CLEANUP
            if member.id == self.bot.user.id and before.channel and not after.channel:
                 guild_id = before.channel.guild.id
                 
                 # 🛡️ 24/7 Rejoin Guard
                 # If disconnected but 24/7 is enabled, we don't clear the player state 
                 # because we might want to auto-rejoin later or keep the queue.
                 # But for now, we follow standard cleanup if 24/7 is OFF.
                 config = ConfigManager.get_server_config(str(guild_id))
                 
                 from music.music import players, now_playing_messages, now_playing_views
                 if guild_id in players:
                     player = players[guild_id]
                     # Only full stop if NOT in 24/7 mode or if specifically cleared
                     if not config.auto_247:
                         player.stop()
                         player.queue.clear()
                         player.current = None
                     else:
                         # 24/7: Just clear playback state but preserve queue
                         if player.voice_client: 
                             try: player.voice_client.stop()
                             except: pass
                         player.current = None
                 
                 # Clean messages (Always do this on disconnect to avoid stale UI)
                 if guild_id in now_playing_messages:
                     try: await now_playing_messages[guild_id].delete()
                     except: pass
                     del now_playing_messages[guild_id]
                 if guild_id in now_playing_views:
                     del now_playing_views[guild_id]
                 
                 logger.info(f"Session Cleanup Filtered: Cleared state for {before.channel.guild.name} (24/7={config.auto_247})")
            return

        if after.channel and self.bot.user in after.channel.members:
            guild_id = after.channel.guild.id
            if not FeatureManager.is_enabled(str(guild_id), "autodj"): return
            player = get_player(guild_id)
            if not player.is_playing and not player.queue:
                await asyncio.sleep(2)
                # Double Check + Lock
                if not player.is_playing and not player.queue:
                    music_cog = self.bot.get_cog("Music")
                    if music_cog:
                        await music_cog._on_song_end(guild_id)

    async def _auto_play_next(self, guild_id: int, player: MusicPlayer):
        if not player.voice_client or not player.voice_client.is_connected(): return
        
        # 🧠 Ask the Brain for the next song
        from music.brain import brain
        
        # Check history size
        history = player.played_history
        
        # Mood Context (Store mood in player if available, else None)
        mood_context = getattr(player, 'active_mood', None) 
        
        # Anchor Context (Last manual song)
        anchor_meta = getattr(player, 'anchor_metadata', None)
        
        next_query = await brain.get_next_song(player.current or player.last_played or {}, history, mood_context, anchor_meta, played_history_set=player.played_ids)
        
        if next_query:
            logger.info(f"Auto-DJ: Brain selected '{next_query}'. Resolving...")
            
            # 🎵 Smart Resolve (JioSaavn/YouTube)
            from music.smart_search import smart_mix
            results = await smart_mix.resolve(next_query, self.bot.user, player)
            
            if results:
                song = results[0]
                song['requester_id'] = str(self.bot.user.id)
                song['is_autodj'] = True
                
                # Add "Auto-DJ" attribution to title for UI clarity if not present
                # (Optional, but "Requester: MELOXI" handles most of it)
                
                player.add_to_queue(song)
                
                # Notify Channel
                try:
                    config = ConfigManager.get_server_config(str(guild_id))
                    channel = self.bot.get_channel(int(config.request_channel_id or 0))
                    if channel:
                         from config.emojis import section, arrow
                         embed = discord.Embed(description=f"{section} **Auto-DJ**\n> {arrow} Added **{song['title']}**", color=settings.COLOR_PRIMARY)
                         embed.set_footer(text="Keeps the vibe going...")
                         await channel.send(embed=embed, delete_after=10)
                except: pass

                if not player.is_playing:
                    # Clear any stale next_callback
                    player.next_callback = None
                    
                    music_cog = self.bot.get_cog("Music")
                    if music_cog:
                        async def next_cb(): 
                             logger.info(f"Auto-DJ: Song ended in {guild_id}, triggering next...")
                             await music_cog._on_song_end(guild_id)
                             
                        player.next_callback, player.bot_loop = next_cb, self.bot.loop
                        logger.info(f"Auto-DJ: Starting playback of '{song['title']}'")
                        await player.play_next()
                    else:
                        logger.error("Auto-DJ: Critical Error - Music Cog not found for playback trigger!")
        else:
            logger.info("Auto-DJ: Brain return empty. Stopping.")

# ==============================================================================
# 👂 SUGGESTIONS COG (Consolidated)
# ==============================================================================

class Suggestions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name="suggestions")
    async def suggestions_cmd(self, ctx: commands.Context, state: str):
        """Toggle automatic suggestions on/off."""
        enabled = state.lower() in ["on", "enable"]
        FeatureManager.set_enabled(str(ctx.guild.id), "suggestions", enabled)
        await ctx.send(embed=create_success_embed(None, f"Suggestions are now **{'Enabled' if enabled else 'Disabled'}**.", user=ctx.author), delete_after=10)

    @commands.hybrid_command(name="suggest")
    async def suggest_cmd(self, ctx: commands.Context):
        """Get 5 song recommendations based on what's playing."""
        await ctx.defer()
        player = get_player(ctx.guild.id)
        if not player.current:
            return await ctx.send(embed=create_error_embed(None, "Play some music first to get recommendations!", user=ctx.author), delete_after=10)

        # Ensure we have suggestions
        if not hasattr(player, '_last_suggestions') or not player._last_suggestions:
             # If no cached suggestions, try to trigger a quick hydration or search
             # But usually _hydrate_suggestions runs on track start.
             # Let's search if empty
             results = await player.search_youtube(f"{player.current.get('title', '')} Mix", limit=5, is_autodj=True)
             player._last_suggestions = results

        songs = player._last_suggestions[:5]
        if not songs:
            return await ctx.send(embed=create_error_embed(None, "Could not find any recommendations right now.", user=ctx.author), delete_after=10)

        desc = ""
        for i, s in enumerate(songs, 1):
            desc += f"`{i}.` **{s.get('title')}**\n> {arrow} {s.get('uploader') or s.get('artist') or 'Unknown Artist'}\n"

        embed = create_embed(
            title="Recommended for You",
            description=f"Based on: **{player.current.get('title')}**\n\n{desc}",
            user=ctx.author,
            bot_user=self.bot.user
        )
        
        view = discord.ui.View()
        view.add_item(views.SuggestionDropdown(self.bot, ctx.guild.id, songs))
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Music(bot))
    await bot.add_cog(Mood(bot))
    await bot.add_cog(AutoDJ(bot))
    await bot.add_cog(Suggestions(bot))
