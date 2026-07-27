"""
Music Player Utility.
Wraps yt-dlp and manages audio sources, queue, and playback state.
"""

# ==============================================================================
# 📥 IMPORTS
# ==============================================================================

import asyncio
import time
import collections
from typing import Optional, List, Dict, Callable
from concurrent.futures import ThreadPoolExecutor

import discord
import yt_dlp

from utils.logger import logger

# ==============================================================================
# ⚙️ CONFIGURATION
# ==============================================================================

# Optimized yt-dlp options for streaming
YTDL_OPTS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'nocheckcertificate': True,
    'cookiefile': 'cookies.txt',
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'extract_flat': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'source_address': '0.0.0.0', # Force IPv4 to bypass potential IPv6 blocks
    'force_ipv4': True,
    'socket_timeout': 15, # Increased for JioSaavn reliability
    'retries': 3,
    # 🛡️ BOT DETECTION BYPASS
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web', 'ios', 'mweb'],
            'player_skip': ['webpage', 'configs']
        }
    },
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Sec-Fetch-Mode': 'navigate'
    }
}

# FFMPEG Filters for "Spotify-like" smoothness
# 1. Trim Start/End (Skip intros/outros)
# 2. Fade In/Out (Soft transitions)
# 3. Loudnorm (Normalize volume) - Optional, maybe too heavy? Let's stick to fade/trim first.
# ss = start trim (1.5s), to = end trim (relative check hard in ffmpeg without duration, 
# so we use 'af' filters mostly or pre-calculated args)
# Actually, 'ss' is input seek. 
FFMPEG_OPTS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 10 -reconnect_on_network_error 1',
    'options': '-vn'
}

def get_ffmpeg_opts(duration_sec: int):
    """Generate dynamic FFMPEG options for a specific song."""
    # Simplified to avoid silence issues
    return {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 10 -reconnect_on_network_error 1',
        'options': '-vn'
    }



def validate_audio_source(info: dict, metadata_duration: int = None, strict_suggestions: bool = True) -> bool:
    """
    Strict clean audio validation.
    Returns True if safe to play.
    """
    title = (info.get('title') or '').lower()
    description = (info.get('description') or '').lower()
    duration = info.get('duration', 0)
    categories = info.get('categories', []) or []
    categories = [str(c).lower() for c in categories if c]
    
    # 0. Reject Shorts (Explicit)
    if "#shorts" in title or "shorts" in info.get("webpage_url", ""):
        logger.info(f"Rejected Source '{title}': Detected as #Shorts")
        return False

    # 1. Reject Non-Music Content (User Request: "short podcarsh game video etcx nhe")
    # Categories check (YouTube often categorizes things as Gaming, People & Blogs, etc)
    # If it's explicitly Gaming or Podcast, reject.
    bad_categories = ["gaming", "podcast", "vlogs", "news", "politics"]
    if any(c in categories for c in bad_categories):
        logger.info(f"Rejected Source '{title}': Non-Music category ({categories})")
        return False

    # 2. Reject Bad Keywords in Title/Description
    # This Helps filter out "Joe Rogan Podcast" or "Elden Ring Gameplay"
    bad_keywords = [
        "podcast", "episode", "full album", "compilation", "vlog", 
        "gameplay", "walkthrough", "tutorial", "stream archive",
        "live stream", "reaction"
    ]
    if any(kw in title for kw in bad_keywords) or any(kw in description for kw in bad_keywords):
        # Exception: "Official Music Video" is fine, but "Official Video Podcast" is not.
        # We check title AND description for high confidence.
        if "podcast" in title or "gameplay" in title:
            logger.info(f"Rejected Source '{title}': Bad Keyword detected")
            return False
            
    # 3. Strict Duration Limits (User Request)
    # Min: 60s (Avoid 30-40s clips)
    # Max: 1200s (Avoid 1 hr mixes, want "Full Song" not "Full Album")
    if strict_suggestions:
        if duration < 60:
             logger.info(f"Rejected Source '{title}': Too short ({duration}s)")
             return False
        if duration > 1200:
             logger.info(f"Rejected Source '{title}': Too long ({duration}s)")
             return False

    # 4. Duration Match (if Metadata exists)
    if metadata_duration and duration:
        yt_dur = duration # Seconds
        meta_dur = metadata_duration / 1000 # MS to Seconds
        
        diff = abs(yt_dur - meta_dur)
        if diff > 15: # Loose Tolerance +-15s (Videos often have intros)
            logger.info(f"Rejected Source '{title}': Duration Mismatch (YT: {yt_dur}s, Brain: {meta_dur}s)")
            return False
            
    return True

def calculate_quality_score(info: dict, brain_meta: dict = None, query: str = "") -> int:
    """
    Calculate a quality score for a search result to find the 'Best of Best'.
    Higher score = Better candidate.
    """
    score = 0
    title = (info.get('title') or '').lower()
    uploader = (info.get('uploader') or '').lower()
    channel = (info.get('channel') or '').lower()
    query_lower = query.lower()
    
    # 0. Query Exact/Partial Match Bonus (100% Accuracy)
    if query_lower and query_lower in title:
        score += 80 # Massive boost for exact query containment
    
    # 1. Brain Metadata Alignment (Highest Priority)
    if brain_meta:
        b_title = getattr(brain_meta, 'title', '').lower()
        b_artist = getattr(brain_meta, 'artist', '').lower()
        
        # Boost if title matches
        if b_title in title:
            score += 50
        # Boost if both match (Very High Confidence)
        if b_title and b_artist and b_title in title and b_artist in title:
            score += 60
        # Boost if uploader is artist
        if b_artist and (b_artist in uploader or b_artist in channel):
            score += 40

    # 2. Authority Boost (Premium Professional)
    if "topic" in uploader or "topic" in channel:
        score += 150 # Massive boost for YouTube-generated high-fidelity tracks
    if "vevo" in uploader or "vevo" in channel:
        score += 80 
        
    # 3. YouTube Music / Official Release Signals
    official_signals = ["official audio", "official music video", "official video", "high definition", "4k", "re-mastered", "remastered"]
    if any(sig in title for sig in official_signals):
        score += 50
    
    if "official audio" in title:
        score += 20 # Extra stack for clean audio
        
    # 4. Priority: Indian/Bollywood/Hindi boost (Optional)
    indian_labels = [
        "t-series", "zee music", "yrf", "sony music india", "tips official", 
        "venus", "eros now", "saregama", "hindi", "bollywood", "punjabi", "indian",
        "tseries", "speed records", "shemaroo", "aditya music", "lahari music"
    ]
    
    is_indian = any(k in title or k in uploader or k in channel for k in indian_labels)
    if is_indian:
        score += 50 # Moderate Boost 
        
    # 5. Query-Aware Negative Signals (100% Search Accuracy)
    # Only penalize these words if the user DID NOT explicitly ask for them in the query.
    penalties = {
        "cover": -100,      # Strict check for covers
        "lyrics": -20,
        "8d": -50,
        "slowed": -40,
        "reverb": -40,
        "live": -50,
        "karaoke": -80,
        "instrumental": -60,
        "remix": -40        # Handled specifically below for brain_meta
    }
    
    for word, pen in penalties.items():
        if word in title:
            # If the user explicitly searched for "slowed" or "cover", DO NOT PENALIZE.
            if word not in query_lower:
                score += pen
                
    # Extra brain_meta remix check (Keep existing logic just in case)
    if "remix" in title and (brain_meta and "remix" not in getattr(brain_meta, 'title', '').lower()) and "remix" not in query_lower:
        score -= 40
        
    return score




# ==============================================================================
# 🎵 MUSIC PLAYER CLASS
# ==============================================================================

class MusicPlayer:
    """
    Handles music playback for a single guild.
    """
    
    def __init__(self, guild_id: int):
        self.guild_id = guild_id
        
        # Queue Management
        self.queue = collections.deque()
        self.current: Optional[Dict] = None
        self.last_played: Optional[Dict] = None
        self.played_history = collections.deque(maxlen=50) # Track last 50 songs
        self.played_ids = set() 
        self.skip_votes = set()
        
        # Mood Lock State
        self.active_mood: Optional[str] = None
        self.mood_lock_source: str = "none" # 'user', 'auto'
        
        # Language/Genre Lock (Anchor)
        self.anchor_metadata: Optional[dict] = None # Stores the metadata of the last MANUALLY played song
        
        # State
        self.voice_client: Optional[discord.VoiceClient] = None
        self.loop = False
        self.force_stop = False
        self.volume = 0.5 # Default 50% (User requested)
        
        # Time Tracking
        self.start_time: float = 0
        self.elapsed_time: float = 0
        self.pause_start_time: float = 0
        
        # Async Helpers
        self.next_callback: Optional[Callable] = None
        self.bot_loop: Optional[asyncio.AbstractEventLoop] = None
        self._executor = ThreadPoolExecutor(max_workers=2)
        self.play_lock = asyncio.Lock()
        self.auto_dj_lock = asyncio.Lock()

    # ==========================================================================
    # 🔍 SEARCH
    # ==========================================================================
    
    # ==========================================================================
    # 🔍 SEARCH
    # ==========================================================================
    
    async def search_youtube(self, query: str, limit: int = 1, is_autodj: bool = False) -> List[Dict]:
        """Search YouTube for songs, with Brain enhancement."""
        # 1. Brain Pre-Processing (Smart Search)
        # Only for text queries, not URLs
        is_url = query.startswith(("http://", "https://"))
        resolved_metadata = None
        
        if not is_url or "jiosaavn.com" in query:
            try:
                # Import here to avoid circular dependency risks during init
                from music.brain import brain
                from difflib import SequenceMatcher
                
                logger.debug(f"Player: Resolving metadata for '{query}'...")
                resolved_metadata = await brain.resolve_song(query)
                
                # Smart Query Switch: Only override if query is simple and resolution is accurate
                keywords = ["remix", "mix", "lyrics", "live", "bass", "reverb", "slowed", "version", "lofi", "3d", "8d"]
                if not any(k in query.lower() for k in keywords):
                    original_query = query
                    new_query = resolved_metadata.search_query
                    
                    # 🛡️ SIMILARITY GUARD
                    # If the resolved metadata title/artist is completely different from the query, 
                    # it's likely a bad match (e.g. "rajana from do pati" -> "Silly Hoes")
                    sim_score = SequenceMatcher(None, original_query.lower(), new_query.lower()).ratio()
                    
                    # If query is short but resolution is totally different, keep original
                    if sim_score < 0.2 and len(original_query) > 5:
                         logger.debug(f"Player: Low Similarity ({sim_score:.2f}) - Using original query '{original_query}' instead of '{new_query}'")
                    else:
                         query = new_query
                         logger.debug(f"Player: Optimized Query: '{query}' (was '{original_query}')")
                else:
                    logger.debug(f"Player: Keeping User Query (Specific version requested): '{query}'")
            except Exception as e:
                logger.error(f"Brain Resolution Failed: {e}")
                # Fallback to original query
                pass

        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(self._executor, lambda: self._search_sync(query, limit, brain_meta=resolved_metadata, is_autodj=is_autodj))
        
        # Enrich results with Brain Metadata
        if resolved_metadata and results:
            for r in results:
                # Enrich results with Brain Metadata (INTERNAL ONLY)
                r['metadata'] = {
                    'title': resolved_metadata.title,
                    'artist': resolved_metadata.artist,
                    'tags': resolved_metadata.tags,
                    'mbid': resolved_metadata.mbid,
                    'duration': resolved_metadata.duration
                }
                # User Request: Fix "00:00 in Queue"
                # If YT duration is unavailable (extract_flat), use Brain duration
                if not r.get('duration') and resolved_metadata.duration:
                    r['duration'] = resolved_metadata.duration / 1000
                
                # User Request: "jo songs play usika real data dusre ka nhe"
                # Similarity Guard: Only overwrite if the YT result is actually a match for the Spotify metadata
                from difflib import SequenceMatcher
                meta_title = resolved_metadata.title.lower()
                yt_title = r.get('title', '').lower()
                
                # Check if meta_title is in yt_title or high similarity
                sim = SequenceMatcher(None, meta_title, yt_title).ratio()
                is_match = sim > 0.6 or meta_title in yt_title or any(word in yt_title for word in meta_title.split() if len(word) > 3)

                if is_match:
                    # For Spotify/YouTube metadata, we can trust it more for display (Clean English Names)
                    if resolved_metadata.title: r['title'] = resolved_metadata.title
                    if resolved_metadata.artist: r['artist'] = resolved_metadata.artist
                    if resolved_metadata.album: r['album'] = resolved_metadata.album
                    
                    # User Request: "spotify wala thumbnail use kro jio savan ka nhe"
                    # Only if it's a confirmed match!
                    if resolved_metadata.thumbnail and "spotify" in resolved_metadata.source:
                        r['thumbnail'] = resolved_metadata.thumbnail
                else:
                    # If it's a mismatched result, WE MUST keep the YouTube title/thumbnail so the user knows what's playing
                    logger.warning(f"Metadata Guard: Low similarity ({sim:.2f}) between Spotify '{meta_title}' and YouTube '{yt_title}'. Keeping YouTube metadata.")
                
        return results

    def _search_sync(self, query: str, limit: int, brain_meta: any = None, is_autodj: bool = False) -> List[Dict]:
        """Internal synchronous search."""
        opts = YTDL_OPTS.copy()
        opts['extract_flat'] = "in_playlist" # Fast extraction (meta only) for ranking
        
        # URL Logic
        if query.startswith(("http://", "https://")):
             opts['extract_flat'] = False # URLs need full info usually? Or not? Let's keep URLs safe.
        
        # Search Enhancement
        if "http" not in query:
             query = self._enhance_bollywood_search(query)
             # FORCE ytmsearch: (YouTube Music) for high quality music only
             # User Request: "serach me only music hi aaye"
             if not query.startswith(("ytsearch:", "ytmsearch:")):
                query = f"ytsearch:{query}"

        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(query, download=False)
                if not info: return []
                
                entries = []
                if 'entries' in info:
                    # Fetch fewer candidates for ranking to speed up search
                    fetch_limit = limit + 2
                    if fetch_limit > 5: fetch_limit = 5
                    entries = list(info['entries'])[:fetch_limit]
                else:
                    entries = [info]
                
                # Capture Related Videos for Autoplay Suggestions
                related = info.get('related_videos') or []
                
                # 1. Filter & Score
                candidates = []
                for e in entries:
                    if not e: continue
                    
                    e['title'] = self._clean_title(e.get('title', 'Unknown'))
                    
                    # Validation
                    if not validate_audio_source(e, strict_suggestions=(limit > 1)):
                         continue
                         
                    # 🚦 ZERO REPEAT ENFORCEMENT (Auto-DJ ONLY)
                    # If Auto-DJ requests this, ensure we NEVER fetch something we already played
                    if is_autodj and e.get('id') in self.played_ids:
                         logger.info(f"Zero-Repeat Guard: Rejected '{e.get('title')}' - Already in played_ids")
                         continue

                    # Score
                    score = calculate_quality_score(e, brain_meta=brain_meta, query=query)
                    e['_quality_score'] = score
                    candidates.append(e)

                # 2. Sort by Score (Desc)
                candidates.sort(key=lambda x: x.get('_quality_score', 0), reverse=True)
                
                if not candidates: return []
                
                # 3. Format Top Results
                results = []
                for e in candidates[:limit]:
                    # Robust Thumbnail Extraction (Sorted by Quality)
                    thumb = None
                    thumbs = e.get('thumbnails') or []
                    
                    # Sort by: 1. Is Landscape? 2. Height
                    valid_thumbs = [t for t in thumbs if t.get('url')]
                    
                    def sort_key(t):
                        h = t.get('height', 0) or 0
                        w = t.get('width', 0) or 0
                        # Prefer wide (16:9) and high resolution
                        is_landscape = 1.5 if (h > 0 and 1.5 < w/h < 1.9) else (1.0 if (h > 0 and w/h > 1.2) else 0)
                        return (is_landscape, h, w) # Landscape -> Height -> Width
                        
                    valid_thumbs.sort(key=sort_key, reverse=True)
                    
                    if valid_thumbs:
                        thumb = valid_thumbs[0]['url']
                    else:
                        thumb = e.get('thumbnail')
                    
                    if not thumb:
                        from config.assets import DEFAULT_THUMBNAIL
                        thumb = DEFAULT_THUMBNAIL
                    
                    results.append({
                        'id': e.get('id'),
                        'webpage_url': e.get('webpage_url') or e.get('url'),
                        'title': e.get('title'),
                        'duration': e.get('duration', (brain_meta.duration / 1000) if brain_meta and brain_meta.duration else 0),
                        'thumbnail': thumb,
                        'uploader': e.get('uploader'),
                        'artist': e.get('artist'),
                        'album': e.get('album'),
                        'is_live': e.get('is_live', False),
                        'score': e.get('_quality_score') # Debug purpose
                    })
                return results
            except Exception as e:
                logger.error(f"Search Error: {e}")
                return []

    # ==========================================================================
    # ⏯️ PLAYBACK CONTROL
    # ==========================================================================
    
    async def play_next(self) -> bool:
        """
        Play the next song in queue. 
        Thread-safe and loop-based to avoid recursion.
        Returns True if a song successfully started playing.
        """
        # Fast fail if already playing (Silent to avoid log spam)
        if self.is_playing: 
            return False

        logger.info("Processing queue for next song...")

        async with self.play_lock:
            # Double check inside lock
            if self.is_playing: 
                return False
            
            # Loop check
            if self.loop and self.current:
                self.queue.appendleft(self.current)
                
            while self.queue:
                # 1. Pop Next
                self.current = self.queue.popleft()
                self.last_played = self.current
                if self.current:
                    title = self.current.get('title')
                    artist = self.current.get('artist', 'Unknown')
                    display = self.current.get('display_string') or f"{title} - {artist}"
                    
                    video_id = self.current.get('id')
                    
                    if title:
                        # [IMPROVED] Store full display string to distinguish between same-titled songs by different artists
                        self.played_history.append(display)
                    if video_id:
                        self.played_ids.add(video_id)
                self.skip_votes.clear()
                
                # 2. Fetch Url
                try:
                    loop = asyncio.get_running_loop()
                    stream_url, full_info = await loop.run_in_executor(
                        self._executor, 
                        lambda: self._get_stream_url(self.current['webpage_url'])
                    )
                    
                    if not stream_url:
                        # 🔄 FALLBACK LOGIC
                        # If this was a JioSaavn song that failed, try YouTube
                        if self.current.get('source') == 'jiosaavn' or 'jiosaavn' in self.current.get('webpage_url', ''):
                             logger.info(f"Processing Fallback for '{self.current.get('title')}': Saavn failed, trying YouTube...")
                             
                             fallback_url = self.current.get('_fallback_webpage_url')
                             if fallback_url:
                                  # Directly use the pre-resolved URL
                                  stream_url, full_info = await loop.run_in_executor(
                                      self._executor, 
                                      lambda: self._get_stream_url(fallback_url)
                                  )
                             else:
                                  # Fallback to search
                                  fallback_results = await self.search_youtube(self.current['title'], limit=1)
                                  if fallback_results:
                                       self.current = fallback_results[0]
                                       # Retry extraction with YouTube source
                                       stream_url, full_info = await loop.run_in_executor(
                                           self._executor, 
                                           lambda: self._get_stream_url(self.current['webpage_url'])
                                       )
                        
                        if not stream_url:
                             logger.warning(f"Skipping {self.current.get('title')} (Source Resolution Failed)")
                             await asyncio.sleep(0.5)
                             continue # Try next song
                    
                    # Update Metadata (Protect Display Data)
                    # [Master Prompt] display data MUST come from Spotify or YT ONLY.
                    if full_info:
                        is_saavn = "jiosaavn.com" in self.current.get('webpage_url', '') or self.current.get('source') == 'jiosaavn'
                        
                        # Only allow update of basic info if not Saavn
                        if not is_saavn:
                            # User Request: "meta data bi song ka chal rha usi ka show kro" (Sync metadata with actual audio)
                            # Logic: If we have Spotify ID, we usually keep it. 
                            # BUUT if the actual audio duration differs significantly (>5s), it's likely a mismatch/wrong version.
                            # In that case, we MUST overwrite with the actual audio metadata to avoid confusion.
                            
                            playing_dur = full_info.get('duration', 0)
                            meta_dur = self.current.get('duration', 0)
                            
                            # User Request: Lock clean metadata. 
                            # Only update title/artist if we have NO brain/spotify metadata at all
                            should_update_display = not self.current.get('metadata') and not self.current.get('spotify_id')
                            
                            if should_update_display:
                                self.current['title'] = self._clean_title(full_info.get('title', self.current['title']))
                                self.current['artist'] = full_info.get('uploader', self.current['artist'])
                                
                                # Thumbs
                                thumbs = full_info.get('thumbnails') or []
                                valid_thumbs = [t for t in thumbs if t.get('url')]
                                def sort_key_play(t):
                                    h = t.get('height', 0) or 0
                                    w = t.get('width', 0) or 0
                                    is_landscape = 1 if (h > 0 and w/h > 1.2) else 0
                                    return (is_landscape, h)
                                valid_thumbs.sort(key=sort_key_play, reverse=True)
                                if valid_thumbs:
                                    self.current['thumbnail'] = valid_thumbs[0]['url']
                                else:
                                    self.current['thumbnail'] = full_info.get('thumbnail', self.current['thumbnail'])

                        if isinstance(full_info, dict):
                            self.current['duration'] = full_info.get('duration', self.current.get('duration', 0))
                            self.current['is_live'] = full_info.get('is_live', self.current.get('is_live', False))
                            self.current['related'] = full_info.get('related_videos', []) or []

            # 3. Play
                    if not self.voice_client or not self.voice_client.is_connected():
                         logger.warning("Voice disconnected. Abort.")
                         return False

                    if not discord.opus.is_loaded():
                         try: discord.opus.load_opus('libopus.dylib')
                         except: pass
                    
                    # Prepare Headers to avoid 403
                    
                    # Prepare Headers to avoid 403
                    # DYNAMIC FFMPEG OPTS for Trim/Fade
                    duration = self.current.get('duration', 0)
                    ffmpeg_opts = get_ffmpeg_opts(duration)
                    
                    if full_info and 'http_headers' in full_info:
                        headers = full_info['http_headers']
                        ua = headers.get('User-Agent', 'Mozilla/5.0')
                        
                        # Simplify: Only use User-Agent. Complex headers often cause 403 in FFmpeg
                        original_before = ffmpeg_opts['before_options']
                        ffmpeg_opts['before_options'] = f'{original_before} -user_agent "{ua}"'
                    else:
                        pass

                    source = discord.FFmpegPCMAudio(stream_url, **ffmpeg_opts)
                    volume_source = discord.PCMVolumeTransformer(source, volume=self.volume)
                    
                    self.voice_client.play(volume_source, after=self._after_playback)
                    logger.info(f"Started playback: {self.current.get('title')}")
                    
                    # BRAIN MEMORY 🧠
                    try:
                        from music.brain import brain
                        await brain.record_play(self.guild_id, self.current)
                    except Exception as e:
                        logger.error(f"Memory Record Error: {e}")

                    self.start_time = time.time()
                    self.elapsed_time = 0
                    
                    return True # Success
                    
                except Exception as e:
                    logger.error(f"Playback Error: {e}")
                    await asyncio.sleep(0.5)
                    continue # Try next song
            
            # Queue Empty
            self.current = None
            return False

    def _cleanup_ffmpeg(self):
        """Ensure the FFmpeg source and process are terminated cleanly."""
        if not self.voice_client:
            return
        source = getattr(self.voice_client, 'source', None)
        if not source:
            return

        proc = getattr(source, 'proc', None)
        if proc:
            try:
                proc.kill()
            except Exception:
                pass
            try:
                proc.wait(timeout=1)
            except Exception:
                pass

        try:
            source.cleanup()
        except Exception:
            pass

    def _get_stream_url(self, url: str) -> tuple[Optional[str], Optional[dict]]:
        """Resolve actual stream URL and return full info."""
        opts = YTDL_OPTS.copy()
        opts['extract_flat'] = False # Need full info for stream
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                if not info:
                    logger.warning("yt-dlp returned no info dict.")
                    return None, None
                    
                stream_url = info.get('url')
                if not stream_url:
                    # Fallback for some sites or formats (manifests)
                    if 'entries' in info:
                         entry = info['entries'][0]
                         stream_url = entry.get('url')
                         info = entry # Use the specific video info
                    elif 'formats' in info:
                         # Pick best audio
                         stream_url = info['formats'][0].get('url')
                
                if not stream_url:
                     logger.warning(f"Failed to extract URL. Keys: {list(info.keys())}")
                
                return stream_url, info
                
            except Exception as e:
                logger.error(f"Error extracting stream URL: {e}")
                return None, None

    def _after_playback(self, error):
        """Callback when audio finishes."""
        if error:
            logger.error(f"FFmpeg Error: {error}")
            self._cleanup_ffmpeg()
        
        if self.next_callback and self.bot_loop:
             future = asyncio.run_coroutine_threadsafe(self.next_callback(), self.bot_loop)
             try: future.result()
             except Exception: pass

    # ==========================================================================
    # 🎮 CONTROLS
    # ==========================================================================

    def pause(self):
        """Pause audio."""
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.pause()
            self.pause_start_time = time.time()

    def resume(self):
        """Resume audio."""
        if self.voice_client and self.voice_client.is_paused():
            self.voice_client.resume()
            self.start_time += (time.time() - self.pause_start_time)
            self.pause_start_time = 0

    async def skip(self):
        """Skip current song with intelligence."""
        if self.voice_client and (self.voice_client.is_playing() or self.voice_client.is_paused()):
            
            # SMART SKIP LOGIC 🧠
            # If skipped early (< 15% or < 30s whatever is less), record as "Hated"
            try:
                if self.current:
                    duration = self.current.get('duration', 0)
                    progress = self.get_progress() # 0.0 to 1.0
                    
                    is_early_skip = False
                    if duration > 30 and progress < 0.15: # Skipped in first 15%
                        is_early_skip = True
                    elif duration < 30 and progress < 0.5: # Short song skipped halfway
                        is_early_skip = True
                        
                    if is_early_skip:
                         logger.info(f"Smart Skip: User hated '{self.current.get('title')}'. Recording feedback.")
                         from utils.brain import brain
                         await brain.record_skip(self.guild_id, self.current)
            except Exception as e:
                logger.error(f"Smart Skip Error: {e}")

            self.voice_client.stop() # This triggers _after_playback

    def stop(self):
        """Stop and clear queue."""
        self.queue.clear()
        self.loop = False
        self.force_stop = True # Set flag to prevent AutoDJ
        self.current = None
        if self.voice_client and (self.voice_client.is_playing() or self.voice_client.is_paused()):
             self.voice_client.stop()
        self._cleanup_ffmpeg()

    def add_to_queue(self, song: Dict):
        """Append song to queue."""
        self.queue.append(song)

    # ==========================================================================
    # 📊 STATUS HELPERS
    # ==========================================================================

    @property
    def is_playing(self) -> bool:
        return self.voice_client and self.voice_client.is_playing()

    @property
    def is_paused(self) -> bool:
        return self.voice_client and self.voice_client.is_paused()
    
    def get_progress(self) -> float:
        """Get current progress (0.0 to 1.0)."""
        if not self.current: return 0.0
        if not (self.is_playing or self.is_paused): return 0.0
        
        if self.is_paused:
             current_elapsed = self.elapsed_time + (self.pause_start_time - self.start_time)
        else:
             current_elapsed = time.time() - self.start_time
             
        duration = self.current.get('duration', 1)
        if duration == 0: return 0.0
        return min(current_elapsed / duration, 1.0)
    
    def get_queue_list(self) -> List[Dict]:
        """Get raw queue list for embeds."""
        return list(self.queue)

    def _clean_title(self, title: str) -> str:
        """
        Remove unnecessary text from titles for a simpler look.
        Preserves original script (Latin/Devanagari).
        """
        import re
        
        # 1. Aggressive Bracket/Parentheses Removal (if they contain junk)
        # Keywords that indicate "unwanted" metadata in brackets
        junk_keywords = [
             'video', 'lyric', 'audio', 'full', 'official', 'hd', '4k', 
             'teaser', 'promo', 'song', 'version', 'release', 'music',
             'prod', 'feat', 'ft.' # People often prefer clean names without 'ft' either
        ]
        
        # Regex to find (...) or [...]
        # We only remove if it contains one of the junk keywords
        def bracket_filter(match):
            content = match.group(0).lower()
            if any(k in content for k in junk_keywords):
                return "" # Remove the entire bracket
            return match.group(0) # Keep (it might be part of the actual name)
            
        title = re.sub(r'[\(\[].*?[\)\]]', bracket_filter, title)
        
        # 2. Specific leftover junk (not in brackets)
        leftover_junk = [
            "Official Music Video", "Official Video", "Video Song", "Audio Song",
            "Lyrical Video", "Full Song", "Music Video", "4K Video", "HD Video",
            "|", ":" # Separators
        ]
        for j in leftover_junk:
            title = re.sub(re.escape(j), "", title, flags=re.IGNORECASE)
            
        # 3. Final cleanup of whitespace and separators
        title = title.replace("  ", " ").strip()
        title = re.sub(r'\s+', ' ', title) # Collapse spaces
        
        return title.strip() or "Unknown Title"

    def _enhance_bollywood_search(self, query: str) -> str:
        """Removed forced hindi bollywood append to allow exact matches."""
        # User requested exact matches: "jo songs likhe voi song playe"
        return query