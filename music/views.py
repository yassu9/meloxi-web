import discord
import asyncio
from typing import Optional, TYPE_CHECKING
from utils.logger import logger
from utils.config_manager import ConfigManager
from utils.features import FeatureManager
from ui.embeds import (
    create_success_embed, create_error_embed, create_now_playing_embed, 
    create_song_added_embed, create_info_embed
)
from config.emojis import (
    EMOJI_PLAYING, EMOJI_PAUSED, EMOJI_LOOP, LABEL_PAUSE, LABEL_PLAY
)
import config.settings as settings # Fix NameError

if TYPE_CHECKING:
    from music.music import MusicPlayer

# This will be set by commands.py to avoid circular imports
_get_player_func = None

def get_player(guild_id: int):
    if _get_player_func:
        return _get_player_func(guild_id)
    return None

class SuggestionDropdown(discord.ui.Select):
    """Dropdown for Smart Suggestions."""
    def __init__(self, bot, guild_id, songs):
        options = []
        for s in songs[:5]:
            label = s.get("title", "Unknown")[:95]
            desc = s.get("uploader", "Unknown")[:95]
            val = s.get("webpage_url") or s.get("url") or s.get("title")
            if len(val) > 100: val = val[:100]
            options.append(discord.SelectOption(label=label, description=desc, value=val, emoji="🎵"))

        super().__init__(placeholder="Recommended for you (Select to Play)", min_values=1, max_values=1, options=options, custom_id="suggestion_select", row=0)
        self.bot = bot
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        player = get_player(self.guild_id)
        if not player: return
        
        query = self.values[0]
        status_msg = await interaction.followup.send(f"Adding suggestion to queue...", ephemeral=False)
        
        try:
            results = await player.search_youtube(query, limit=1)
            if results:
                song = results[0]
                song['requester_id'] = str(interaction.user.id)
                player.add_to_queue(song)
                try: await status_msg.delete()
                except: pass
                
                channel = interaction.channel
                await channel.send(embed=create_song_added_embed(song, len(player.queue), interaction.user, self.bot.user), delete_after=10)
                if not player.current:
                    await player.play_next()
                    music_cog = self.bot.get_cog("Music")
                    if music_cog:
                        await music_cog._update_now_playing(interaction, guild_id=self.guild_id, send_new=True)
        except Exception as e:
            try: await status_msg.edit(content=f"Failed to load suggestion: {e}")
            except: pass

class QueueListView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=15) # Auto-expire in 15s
        self.bot = bot
        self.guild_id = guild_id
        self.message = None

    async def on_timeout(self):
        if self.message:
            try: await self.message.delete()
            except: pass

    @discord.ui.button(label="Refresh", emoji="🔄", style=discord.ButtonStyle.secondary)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Reset Timeout
        self.timeout = 15
        
        player = get_player(self.guild_id)
        if not player or not player.queue:
             embed = create_error_embed("Queue Empty", "The queue is currently empty.")
             await interaction.response.edit_message(embed=embed, view=None)
             return

        queue_list = list(player.queue)
        desc = ""
        for i, song in enumerate(queue_list, 1):
            title = song.get('title', 'Unknown')
            duration = int(song.get('duration', 0))
            d_str = f"{duration//60}:{duration%60:02d}"
            req_id = song.get("requester_id")
            requester_name = "Unknown"
            if req_id:
                user = self.bot.get_user(int(req_id))
                if user: requester_name = user.name
            desc += f"`{i}.` **{title}** | `{d_str}` | {requester_name}\n"

        embed = discord.Embed(title=f"Queue ({len(queue_list)})", description=desc[:4090], color=settings.COLOR_PRIMARY)
        embed.set_footer(text="Click Refresh to update • Auto-closes in 15s")
        await interaction.response.edit_message(embed=embed, view=self)

class QueueCleanupView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=15)
        self.bot = bot
        self.guild_id = guild_id
        self.message = None
        
        player = get_player(guild_id)
        options = []
        if player and player.queue:
            for i, song in enumerate(list(player.queue)[:25]):
                label = song.get('title', 'Unknown')[:95]
                options.append(discord.SelectOption(label=f"{i+1}. {label}", value=str(i), emoji="🗑️"))
        if not options:
            options.append(discord.SelectOption(label="Queue is empty", value="-1"))
        self.add_item(RemoveSongSelect(options))

    async def on_timeout(self):
        if self.message:
            try: await self.message.delete()
            except: pass

    @discord.ui.button(label="Clear All", emoji="🗑️", style=discord.ButtonStyle.danger)
    async def clear_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = get_player(self.guild_id)
        if player:
            player.queue.clear()
        
        # Edit to confirmation then delete
        await interaction.response.edit_message(content="Queue Cleared!", view=None, embed=None)
        cog = self.bot.get_cog("Music")
        if cog: await cog._update_request_channel(self.guild_id)

class RemoveSongSelect(discord.ui.Select):
    def __init__(self, options):
        super().__init__(placeholder="Select songs to remove...", min_values=1, max_values=min(len(options), 25), options=options)

    async def callback(self, interaction: discord.Interaction):
        player = get_player(interaction.guild.id)
        if not player or self.values[0] == "-1":
             await interaction.response.send_message("Queue is already empty.", ephemeral=True)
             return
        indices = sorted([int(v) for v in self.values], reverse=True)
        removed_count = 0
        from collections import deque
        q_list = list(player.queue)
        for idx in indices:
            if idx < len(q_list):
                del q_list[idx]
                removed_count += 1
        player.queue = deque(q_list)
        
        await interaction.response.edit_message(content=f"Removed {removed_count} song(s)!", view=None, embed=None)
        cog = interaction.client.get_cog("Music")
        if cog: await cog._update_request_channel(interaction.guild.id)

class RequestChannelView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.guild_id = guild_id

    def update_buttons(self, player):
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.custom_id:
                if child.custom_id == "req_pause":
                     child.emoji = "▶️" if player.is_paused else "⏸️"
                     child.label = "Resume" if player.is_paused else "Pause"
                     child.style = discord.ButtonStyle.success if player.is_paused else discord.ButtonStyle.secondary
                elif child.custom_id == "req_loop":
                    child.emoji = "🔂" if player.loop else "🔁"
                    child.label = "Loop 1" if player.loop else "Loop"
                    child.style = discord.ButtonStyle.success if player.loop else discord.ButtonStyle.secondary
                elif child.custom_id == "req_autoplay":
                     enabled = FeatureManager.is_enabled(str(self.guild_id), "autodj")
                     child.style = discord.ButtonStyle.success if enabled else discord.ButtonStyle.secondary
                elif child.custom_id == "req_mute":
                     child.style = discord.ButtonStyle.danger if player.volume == 0 else discord.ButtonStyle.secondary

    @discord.ui.button(emoji="✨", label="Autoplay", style=discord.ButtonStyle.secondary, row=0, custom_id="req_autoplay")
    async def autoplay_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        current = FeatureManager.is_enabled(str(self.guild_id), "autodj")
        FeatureManager.set_enabled(str(self.guild_id), "autodj", not current)
        cog = self.bot.get_cog("Music")
        if cog: await cog._update_request_channel(self.guild_id)

    @discord.ui.button(emoji="⏸️", label="Pause", style=discord.ButtonStyle.secondary, row=0, custom_id="req_pause")
    async def pause_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        player = get_player(self.guild_id)
        if player:
            if player.is_paused: player.resume()
            else: player.pause()
        cog = self.bot.get_cog("Music")
        if cog: await cog._update_request_channel(self.guild_id)

    @discord.ui.button(emoji="⏭️", label="Skip", style=discord.ButtonStyle.secondary, row=0, custom_id="req_skip")
    async def skip_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        cog = self.bot.get_cog("Music")
        if cog: await cog._attempt_skip(interaction, self.guild_id, interaction.user)

    @discord.ui.button(emoji="🔁", label="Loop", style=discord.ButtonStyle.secondary, row=0, custom_id="req_loop")
    async def loop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        player = get_player(self.guild_id)
        if player: player.loop = not player.loop
        cog = self.bot.get_cog("Music")
        if cog: await cog._update_request_channel(self.guild_id)

    @discord.ui.button(emoji="⏹️", label="Stop", style=discord.ButtonStyle.danger, row=0, custom_id="req_stop")
    async def stop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        player = get_player(self.guild_id)
        if player:
            player.stop()
            player.queue.clear()
            if player.voice_client:
                await player.voice_client.disconnect()
        cog = self.bot.get_cog("Music")
        if cog: await cog._update_request_channel(self.guild_id)

    @discord.ui.button(emoji="🔉", label="Vol -", style=discord.ButtonStyle.secondary, row=1, custom_id="req_vol_down")
    async def vol_down_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        player = get_player(self.guild_id)
        if player:
            new_vol = max(0, int(player.volume * 100) - 10)
            if player.voice_client and player.voice_client.source:
                player.voice_client.source.volume = new_vol / 100
            player.volume = new_vol / 100
        cog = self.bot.get_cog("Music")
        if cog: await cog._update_request_channel(self.guild_id)

    @discord.ui.button(emoji="🔊", label="Vol +", style=discord.ButtonStyle.secondary, row=1, custom_id="req_vol_up")
    async def vol_up_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        player = get_player(self.guild_id)
        if player:
            new_vol = min(150, int(player.volume * 100) + 10)
            if player.voice_client and player.voice_client.source:
                player.voice_client.source.volume = new_vol / 100
            player.volume = new_vol / 100
        cog = self.bot.get_cog("Music")
        if cog: await cog._update_request_channel(self.guild_id)

    @discord.ui.button(emoji="🔇", label="Mute", style=discord.ButtonStyle.secondary, row=1, custom_id="req_mute")
    async def mute_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        player = get_player(self.guild_id)
        if player:
            if player.volume > 0:
                if player.voice_client and player.voice_client.source:
                    player.voice_client.source.volume = 0
                player.volume = 0
            else:
                if player.voice_client and player.voice_client.source:
                    player.voice_client.source.volume = 1.0
                player.volume = 1.0
        cog = self.bot.get_cog("Music")
        if cog: await cog._update_request_channel(self.guild_id)

    @discord.ui.button(emoji="📜", label="Queue", style=discord.ButtonStyle.secondary, row=2, custom_id="req_queue")
    async def queue_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer() # Public
        player = get_player(self.guild_id)
        if not player or not player.queue:
             msg = await interaction.followup.send("Queue is empty.", ephemeral=False)
             await asyncio.sleep(5)
             try: await msg.delete()
             except: pass
             return

        queue_list = list(player.queue)
        desc = ""
        for i, song in enumerate(queue_list, 1):
            title = song.get('title', 'Unknown')
            duration = int(song.get('duration', 0))
            d_str = f"{duration//60}:{duration%60:02d}"
            req_id = song.get("requester_id")
            requester_name = "Unknown"
            if req_id:
                user = self.bot.get_user(int(req_id))
                if user: requester_name = user.name
            desc += f"`{i}.` **{title}** | `{d_str}` | {requester_name}\n"

        embed = discord.Embed(title=f"Queue ({len(queue_list)})", description=desc[:4090], color=settings.COLOR_PRIMARY)
        embed.set_footer(text="Updates manually via Refresh button • Auto-closes in 15s")
        
        view = QueueListView(self.bot, self.guild_id)
        msg = await interaction.followup.send(embed=embed, view=view) # Not Ephemeral
        view.message = msg

    @discord.ui.button(emoji="🔀", label="Shuffle", style=discord.ButtonStyle.secondary, row=2, custom_id="req_shuffle")
    async def shuffle_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        player = get_player(self.guild_id)
        if player:
            import random
            random.shuffle(player.queue)
        await interaction.followup.send("Queue Shuffled!", ephemeral=True)

    @discord.ui.button(emoji="🗑️", label="Clear", style=discord.ButtonStyle.secondary, row=2, custom_id="req_clear")
    async def clear_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = get_player(self.guild_id)
        if not player or not player.queue:
             await interaction.response.send_message("Queue is already empty.", ephemeral=True)
             return
             
        # Public View for Clearing
        view = QueueCleanupView(self.bot, self.guild_id)
        msg = await interaction.response.send_message( # Not Ephemeral
            "Manage Queue\nSelect songs to remove OR clear all.", 
            view=view
        )
        # Note: interaction.response.send_message returns None in some versions, 
        # but we need the message for deletion. In Discord.py 2.0+ we can use fetch or followup.
        # Actually interaction.original_response() gets it.
        view.message = await interaction.original_response()

    @discord.ui.button(emoji="🎵", label="Lofi", style=discord.ButtonStyle.secondary, row=3, custom_id="req_lofi")
    async def lofi_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        cog = self.bot.get_cog("Music")
        if cog:
            class MockCtx:
                def __init__(self, interaction):
                    self.guild = interaction.guild
                    self.channel = interaction.channel
                    self.author = interaction.user
                    self.send = interaction.followup.send
                    self.message = interaction.message
                    self.bot = cog.bot
                
                async def defer(self, *args, **kwargs):
                    pass
            await cog.play(MockCtx(interaction), query="Lofi Hip Hop radio")

    @discord.ui.button(emoji="📝", label="Lyrics", style=discord.ButtonStyle.secondary, row=3, custom_id="req_lyrics")
    async def lyrics_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await interaction.followup.send("Searching for lyrics...", ephemeral=True)

class NowPlayingView(discord.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.guild_id = guild_id
    
    def add_suggestions(self, songs):
        for child in self.children:
            if isinstance(child, SuggestionDropdown):
                self.remove_item(child)
        if songs:
            self.add_item(SuggestionDropdown(self.bot, self.guild_id, songs))

    def update_buttons(self, player):
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.custom_id:
                child.disabled = not (player.is_playing or player.is_paused) and not player.current
                if child.custom_id == "btn_pause":
                    child.emoji = "▶️" if player.is_paused else "⏸️"
                    child.style = discord.ButtonStyle.secondary
                elif child.custom_id == "btn_loop":
                    child.emoji = "🔂" if player.loop else "🔁"
                    child.style = discord.ButtonStyle.success if player.loop else discord.ButtonStyle.secondary
    
    async def _check_vc(self, interaction: discord.Interaction) -> bool:
        """Ensure user is in the same VC as the bot."""
        player = get_player(self.guild_id)
        if not player or not player.voice_client:
             await interaction.response.send_message("❌ | I am not connected to a voice channel.", ephemeral=True)
             return False
        
        if not interaction.user.voice or interaction.user.voice.channel != player.voice_client.channel:
             await interaction.response.send_message(f"❌ | You must be in {player.voice_client.channel.mention} to use controls.", ephemeral=True)
             return False
        return True

    @discord.ui.button(emoji="⏸️", label="Pause", style=discord.ButtonStyle.secondary, row=1, custom_id="btn_pause")
    async def pause_resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._check_vc(interaction): return
        await interaction.response.defer()
        player = get_player(self.guild_id)
        if not player or not (player.is_playing or player.is_paused): return await self._refresh_now_playing(interaction, player)
        if player.is_paused: player.resume()
        else: player.pause()
        await self._refresh_now_playing(interaction, player)
    
    @discord.ui.button(emoji="⏭️", label="Skip", style=discord.ButtonStyle.secondary, row=1, custom_id="btn_skip")
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._check_vc(interaction): return
        await interaction.response.defer()
        music_cog = self.bot.get_cog("Music")
        if music_cog:
            await music_cog._attempt_skip(interaction, self.guild_id, interaction.user)
    
    @discord.ui.button(emoji="🔁", label="Loop", style=discord.ButtonStyle.secondary, row=1, custom_id="btn_loop")
    async def loop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._check_vc(interaction): return
        await interaction.response.defer()
        player = get_player(self.guild_id)
        if player:
            player.loop = not player.loop
        await self._refresh_now_playing(interaction, player)
    
    @discord.ui.button(emoji="⏹️", label="Stop", style=discord.ButtonStyle.danger, row=1, custom_id="btn_stop")
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._check_vc(interaction): return
        player = get_player(self.guild_id)
        await interaction.response.defer()
        last_track = player.current if player else None
        
        # 🛡️ 24/7 Enforcement
        config = ConfigManager.get_server_config(str(self.guild_id))
        
        if player:
            player.stop()
            # Disconnect only if 24/7 is OFF
            if player.voice_client and not config.auto_247:
                try: await player.voice_client.disconnect()
                except: pass
        
        music_cog = self.bot.get_cog("Music")
        if music_cog:
            import music.music as music_cmds
            if self.guild_id in music_cmds.now_playing_messages:
                try: 
                    msg = music_cmds.now_playing_messages[self.guild_id]
                    title = last_track.get('title', 'Unknown') if last_track else "Playback Stopped"
                    thumb = last_track.get('thumbnail') if last_track else None
                    status = "Stopped" if not config.auto_247 else "Stopped (24/7)"
                    embed = create_now_playing_embed(
                        song_title=title, duration="0:00", progress=0, thumbnail=thumb, 
                        requester=interaction.user, bot_user=self.bot.user,
                        status_override=status
                    )
                    embed.set_footer(text=f"Stopped by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
                    await msg.edit(embed=embed, view=None)
                except: pass
                del music_cmds.now_playing_messages[self.guild_id]
            if self.guild_id in music_cmds.now_playing_views: del music_cmds.now_playing_views[self.guild_id]
            
            # Refresh Request Channel UI
            await music_cog._update_request_channel(self.guild_id)

    async def _refresh_now_playing(self, interaction: discord.Interaction, player):
        import music.music as music_cmds
        target_message = music_cmds.now_playing_messages.get(self.guild_id)
        if interaction and interaction.message: target_message = interaction.message
        if not target_message or not player: return
        if not player.current:
             if interaction and not interaction.response.is_done():
                 await interaction.response.send_message("Nothing played.", ephemeral=True)
             return
        try:
            song = player.current
            total = int(song.get("duration", 0))
            duration_str = f"{total // 60}:{total % 60:02d}" if total > 0 else "LIVE"
            listeners = 0
            if player.voice_client and player.voice_client.channel:
                 listeners = len([m for m in player.voice_client.channel.members if not m.bot])
            requester_id = song.get("requester_id")
            requester = None
            if requester_id:
                try:
                    requester = self.bot.get_user(int(requester_id))
                    if not requester: requester = await self.bot.fetch_user(int(requester_id))
                except: pass
            status = "Playing"
            if player.is_paused: status = "Paused"
            if player.loop: status = "Looping"
            embed = create_now_playing_embed(
                song_title=song.get("title", "Unknown"), duration=duration_str, requester=requester,
                loop=player.loop, progress=player.get_progress(), thumbnail=song.get("thumbnail"),
                album=song.get("album"), artist=song.get("artist"), bot_user=self.bot.user,
                score=song.get('_quality_score', 0), listeners=listeners, status_override=status,
                source=song.get('source_display') or song.get('source')
            )
            self.update_buttons(player)
            if interaction and not interaction.response.is_done():
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                await target_message.edit(embed=embed, view=self)
        except Exception as e:
            logger.error(f"Refresh Error: {e}")
