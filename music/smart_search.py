"""
Smart Search & Resolution Engine.
Orchestrates Spotify Metadata + JioSaavn Audio.
"""

import asyncio
import re
from typing import Optional, List, Dict, Any
from difflib import SequenceMatcher

from music.spotify_client import spotify
from music.saavn_client import saavn
from music.ai import AIManager
from utils.logger import logger
from config.settings import DEFAULT_FEATURES
import config.settings as settings

class SmartLoader:
    """
    The Brain of the Smart Mix.
    Resolves queries using Spotify for discovery and JioSaavn for playback.
    """
    
    def __init__(self):
        self.cache = {} # Simple in-memory cache for resolved mappings
        self.ai = AIManager()

    async def resolve(self, query: str, user, player=None) -> Optional[List[Dict[str, Any]]]:
        """
        Main resolution entry point.
        Returns a List of Track Dicts or None (Fallback).
        Args:
            query (str): User search query.
            user (User): user object.
            player (MusicPlayer): Optional player instance for fallback searches.
        """
        try:
            # 1. Feature Flag Check
            spotify_on = getattr(settings, "SPOTIFY_ENABLED", True)
            jiosaavn_on = getattr(settings, "JIOSAAVN_GLOBAL_ENABLED", True)
            
            # 2. Check for URLs
            if "spotify.com" in query:
                if not spotify_on: return None
                return await self._handle_spotify_url(query, player)
            
            if "jiosaavn.com" in query:
                if not jiosaavn_on: return None
                return await self._handle_saavn_url(query)
                
            # 3. Text Search (Smart Mix + Mood + Fallback)
            if spotify_on and jiosaavn_on:
                mood = None # Initialize outside AI scope to avoid UnboundLocalError
                
                # 🧠 MOOD DETECTION
                if self.ai.is_enabled():
                    # clean_q = query (Moved initialization to inner scopes where needed or keep local)
                    
                    # A. Explicit Mood Prefix (mood:sad)
                    if query.lower().startswith("mood:"):
                         mood = query.split(":")[1].strip().split(" ")[0] # extract just the mood word
                         # Remove mood:xyz from query to check if there is a song name
                         clean_q = query.replace(f"mood:{mood}", "").strip()
                    # B. Implicit Mood
                    else:
                         mood = await self.ai.suggest_mood(query)
                         clean_q = query
                    
                    if mood:
                        logger.info(f"Smart Resolution: Mood '{mood}' detected.")
                        
                        # Check if it's a "Mood Only" request or "Song + Mood" request
                        # If query is short/generic or just mood words -> Mood Mix
                        is_generic = len(clean_q.split()) < 3 or clean_q.lower() in ["songs", "bollywood", "hindi", "music", mood]
                        
                        if is_generic:
                             # MOOD MIX MODE
                             new_query = await self.ai.suggest_search_query(mood)
                             if new_query: 
                                  logger.info(f"Smart Resolution: Generic Mood -> '{new_query}'")
                                  query = new_query
                        else:
                             # SONG + MOOD MODE
                             # Append context to find the right version (Remix/Lofi/etc)
                             if mood == "party":
                                  query = f"{clean_q} remix fast"
                             elif mood == "sad":
                                  query = f"{clean_q} lofi slowed"
                             elif mood == "romantic":
                                  query = f"{clean_q}" # Keep original for romantic
                             elif mood == "workout":
                                  query = f"{clean_q} gym remix bass"
                             
                             logger.info(f"Smart Resolution: Contextual Song -> '{query}'")

                # 🚀 EXECUTE SMART SOURCE SELECTION
                results = await self._resolve_best_source(query, player)
                
                # Inject Detected Mood into Metadata for Locking 🔒
                if results and mood:
                    for r in results:
                        r['_detected_mood'] = mood
                        
                return results
            
            # If Smart Mix disabled, fallback to None (YouTube)
            return None
            
        except Exception as e:
            logger.error(f"Smart Resolution Error: {e}")
            return None

    async def _handle_spotify_url(self, url: str, player=None) -> Optional[List[Dict[str, Any]]]:
        """Handle Spotify Links (Track/Album/Playlist)."""
        link_type, item_id = spotify.parse_link(url)
        if not link_type or not item_id: return None
        
        tracks_to_process = []
        if link_type == "track":
            meta = await spotify.get_track(item_id)
            if meta: tracks_to_process = [meta]
        elif link_type == "playlist":
            raw_tracks = await spotify.get_playlist_tracks(item_id, limit=30)
            if raw_tracks:
                 tracks_to_process = [{"display_string": t, "search_query": t, "spotify_id": f"pl_{i}", "duration_ms": 0} for i, t in enumerate(raw_tracks)]
        elif link_type == "album":
            raw_tracks = await spotify.get_album_tracks(item_id, limit=30)
            if raw_tracks:
                 tracks_to_process = [{"display_string": t, "search_query": t, "spotify_id": f"al_{i}", "duration_ms": 0} for i, t in enumerate(raw_tracks)]
        
        if not tracks_to_process: return None
        
        resolved_tracks = []
        for meta in tracks_to_process:
            if "artist" in meta: # Single Track
                saavn_track = await self._match_spotify_to_saavn(meta)
                if saavn_track: resolved_tracks.append(saavn_track)
            else: # Playlist Item (String)
                # Search best available audio
                best_audio = await self._resolve_best_source(meta["search_query"], player)
                if best_audio: resolved_tracks.append(best_audio[0])
                
        return resolved_tracks if resolved_tracks else None

    async def _handle_saavn_url(self, url: str) -> Optional[List[Dict[str, Any]]]:
        """Handle Direct JioSaavn Links with UI Sanitization. island."""
        parsed = saavn.parse_link(url)
        if not parsed: return None
        
        type_, token, slug = parsed
        raw_tracks = []
        
        if type_ == "song":
            track = await saavn.get_song(token, slug)
            if track: raw_tracks = [track]
        elif type_ in ["album", "playlist"]:
            data = await saavn.get_album(token, slug) if type_ == "album" else await saavn.get_playlist(token, slug)
            if data and data.get("tracks"): raw_tracks = data["tracks"]
        
        if not raw_tracks: return None
        
        # [Master Prompt] SANITIZE: Display metadata ONLY from Spotify/YT
        sanitized_tracks = []
        for track in raw_tracks:
             # Try to find Spotify/YT equivalent for visuals
             await self._enrich_metadata_safe(track, player)
             sanitized_tracks.append(track)
             
        return sanitized_tracks if sanitized_tracks else None

    async def _enrich_metadata_safe(self, track: Dict[str, Any], player=None):
        """Ensure track metadata is high-fidelity while preserving the real language/script."""
        orig_title = track.get('title', '')
        orig_artist = track.get('artist', '')
        query = f"{orig_title} {orig_artist}"
        
        def has_devanagari(text):
            return any('\u0900' <= char <= '\u097F' for char in text)

        # 1. Try Spotify for visuals and canonical names
        if spotify.is_available():
            sp_meta = await spotify.search_track(query)
            if sp_meta:
                 sp_title = sp_meta.get('title', '')
                 
                 # Purity Guard: If original was English (no Devanagari) but Spotify is Hindi, 
                 # OR if original was Hindi and Spotify is English, be careful.
                 script_mismatch = has_devanagari(orig_title) != has_devanagari(sp_title)
                 
                 track['thumbnail'] = sp_meta.get('thumbnail') or track.get('thumbnail')
                 track['spotify_id'] = sp_meta.get('spotify_id')
                 
                 # Only update title if no script mismatch OR if original was trash
                 if not script_mismatch or not orig_title or len(orig_title) < 2:
                     track['title'] = sp_title
                     track['artist'] = sp_meta.get('artist', track['artist'])
                 return # Success
        
        # 2. Try YouTube search (minimal) for high-res thumbnails if Spotify fails
        # Reuse the caller's source adapter. The web backend provides one, so
        # this shared resolver no longer needs to create a Discord MusicPlayer.
        if player:
            yt_results = await player.search_youtube(query, limit=1)
        else:
            from music.player import MusicPlayer
            yt_results = await MusicPlayer(0).search_youtube(query, limit=1)
        if yt_results:
             yt = yt_results[0]
             yt_title = yt.get('title', '')
             track['thumbnail'] = yt.get('thumbnail') or track.get('thumbnail')
             
             script_mismatch = has_devanagari(orig_title) != has_devanagari(yt_title)
             
             # Only update title/artist if they are currently missing/trash or script matches
             if not orig_title or len(orig_title) < 2 or (not script_mismatch):
                 track['title'] = yt_title
                 track['artist'] = yt.get('artist', track.get('artist'))
        
        # 3. Final visual safety: No Saavn thumbnails (policy)
        if not track.get('spotify_id') and not track.get('thumbnail'):
             track['thumbnail'] = None


    async def _resolve_best_source(self, query: str, player=None) -> Optional[List[Dict[str, Any]]]:
        """
        Executes parallel search on Enabled Sources and selects the BEST candidate.
        1. Spotify Meta -> JioSaavn Audio (Bollywood Specialist)
        2. YouTube Search (Generalist / Video / Fallback)
        """
        
        # Define Tasks
        tasks = [self._handle_text_search(query)] # Task 0: Saavn
        
        if player:
            tasks.append(player.search_youtube(query, limit=1)) # Task 1: YouTube
            
        # Execute Parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Extract Results
        saavn_res = results[0] if isinstance(results[0], list) and results[0] else None
        yt_res = results[1] if len(results) > 1 and isinstance(results[1], list) and results[1] else None
        
        if not saavn_res and not yt_res:
             logger.debug(f"Smart Select: No results found for '{query}' in Saavn or YouTube.")

        # 🏆 SELECTION LOGIC (MASTER PROMPT STEP 4)
        jiosaavn_on = getattr(settings, "JIOSAAVN_ENABLED", True)
        youtube_on = getattr(settings, "YOUTUBE_ENABLED", True)

        # Heuristic: Detect if it's Bollywood/Local
        is_bollywood = False
        saavn_track = saavn_res[0] if saavn_res else None
        
        if saavn_track:
            bollywood_langs = ['hindi', 'punjabi', 'bhojpuri', 'haryanvi', 'bengali', 'telugu', 'tamil', 'marathi', 'gujarati']
            s_lang = saavn_track.get('language', '').lower()
            if s_lang in bollywood_langs:
                 is_bollywood = True
            elif any(k in (saavn_track.get('title', '') + " " + saavn_track.get('artist', '')).lower() for k in ["movie", "soundtrack", "ost", "film", "series"]):
                 is_bollywood = True

        # CASE A: Both Sources Found
        if saavn_res and yt_res:
            yt_track = yt_res[0]
            if is_bollywood and jiosaavn_on:
                 logger.info(f"Smart Select: Bollywood detected -> Selecting JioSaavn (Audio) + YouTube (Metadata)")
                 
                 # [Master Prompt] DISPLAY DATA MUST COME ONLY FROM Spotify/YouTube
                 # If saavn_track doesn't have spotify data (mbid/spotify_id), use YT metadata for UI
                 if not saavn_track.get('spotify_id'):
                     saavn_track['thumbnail'] = yt_track.get('thumbnail')
                     saavn_track['title'] = yt_track.get('title')
                     saavn_track['artist'] = yt_track.get('artist')
                     saavn_track['album'] = yt_track.get('album')
                 
                 saavn_track['_fallback_webpage_url'] = yt_track.get('webpage_url')
                 return saavn_res
            if youtube_on:
                 logger.info(f"Smart Select: Global/Non-Bollywood detected -> Selecting YouTube")
                 return yt_res

        # CASE B: Only Saavn Found
        if saavn_res and jiosaavn_on:
             return saavn_res

             
        # CASE C: Only YouTube Found
        if yt_res and youtube_on:
             return yt_res

        return None

    async def _handle_text_search(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Smart Text Search: Spotify Meta -> Saavn Audio."""
        try:
            # 1. Search Spotify for best Metadata match
            spotify_meta = await spotify.search_track(query)
            
            if not spotify_meta: 
                # Optimization: Should we search Saavn direct? 
                # For now, rely on YouTube as fallback if Spotify fails.
                return None 
            
            # 2. Find Audio on Saavn
            saavn_track = await self._match_spotify_to_saavn(spotify_meta)
            
            if saavn_track:
                return [saavn_track]
            return None
        except Exception as e:
            logger.error(f"Text Search Error: {e}")
            return None

    async def _match_spotify_to_saavn(self, sp_meta: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        The Magic Sauce. Matches Spotify Metadata to JioSaavn Audio.
        Checks: Title, Artist, Duration.
        """
        cache_key = sp_meta.get("spotify_id")
        if cache_key and cache_key in self.cache:
            return self.cache[cache_key]
            
        title = sp_meta.get('title', '') or ''
        artist = sp_meta.get('artist', '') or ''
        query = f"{title} {artist}"
        
        # Search Saavn
        results = await saavn.search(query, limit=5)
        if not results: return None
        
        best_match = None
        best_score = 0
        
        target_title = self._clean_string(title)
        target_artist = artist.lower().split(',')[0].strip() if artist else ""
        target_duration = sp_meta.get('duration_ms', 0) / 1000 # to seconds
        
        for track in results:
            score = 0
            
            # 1. Duration Check (Critical)
            # +/- 10 seconds tolerance (Relaxed for accuracy)
            dur = track.get('duration', 0)
            if target_duration > 0 and abs(dur - target_duration) < 10:
                score += 50
            elif target_duration > 0 and abs(dur - target_duration) < 15:
                score += 20
                
            # 2. Title Match (Fuzzy)
            clean_title = self._clean_string(track.get('title', ''))
            title_sim = SequenceMatcher(None, target_title, clean_title).ratio()
            if title_sim > 0.8: score += 40
            elif title_sim > 0.5: score += 10
            
            # 3. Artist Match (Partial)
            track_artist = track.get('artist', '') or ''
            if target_artist and track_artist and target_artist in track_artist.lower():
                score += 30
                
            # 4. Bollywood Priority (Heuristic) -> [IMPLEMENTED]
            # User Request: First Priority = Bollywood/Hindi/Indian
            bolly_langs = ['hindi', 'punjabi', 'bhojpuri', 'haryanvi', 'bengali', 'telugu', 'tamil', 'marathi', 'gujarati', 'urdu']
            track_lang = track.get('language', '').lower()
            
            if track_lang in bolly_langs:
                score += 50
            
            # [CRITICAL FIX] Strict Language Guard
            # If the best match so far is Bollywood, and this track is English, PENALIZE it.
            # Or better: If our Spotify Target is likely Bollywood, Reject English.
            # We don't verify Spotify Lang yet, but we can assume if query has no descriptors, we want the primary version.
            if track_lang == 'english' and target_artist not in ['justin bieber', 'dua lipa', 'ed sheeran']: # Heuristic
                 # If target artist is clearly Indian (A.R. Rahman check handled by Artist Score), but let's be safe.
                 if any(a in target_artist.lower() for a in ['ar rahman', 'arijit', 'shreya', 'badshah', 'sidhu', 'diljit']):
                      score -= 100 # Kill this match (It's likely a cover/remix in English)

            # Boost for "Bollywood" keyword in album/source
            if "bollywood" in str(track).lower():
                score += 30

            if score > best_score:
                best_score = score
                best_match = track
                
        # Threshold for "Good Enough"
        # Relaxed from 60 to 45 to catch more matches (Remixes/Versions)
        if best_match and best_score > 45:
             # Decorate with Source Info
             best_match['source_display'] = "Spotify ➔ JioSaavn"
             best_match['_smart_match'] = True
             
             # 🎨 USE SPOTIFY THUMBNAIL (Higher Quality / Familiar)
             best_match['thumbnail'] = sp_meta.get('thumbnail')

             # 📛 USE SPOTIFY TITLE/ARTIST (English/Transliterated Standard)
             # User Request: "song name english me kro... jo yt pr play ho rha voi song name"
             # Spotify metadata is usually cleaner and in English script.
             if sp_meta.get('title'):
                 best_match['title'] = sp_meta['title']
             if sp_meta.get('artist'):
                 best_match['artist'] = sp_meta['artist']
             
             if cache_key: self.cache[cache_key] = best_match
             return best_match
             
        return None

    def _clean_string(self, text: str) -> str:
        """Normalize key strings."""
        if not text: return ""
        try:
            text = text.lower()
            # Remove version info
            text = re.sub(r"\(.*?\)", "", text) # Remove (...)
            text = re.sub(r"\[.*?\]", "", text) # Remove [...]
            text = text.replace("official video", "").replace("lyrical", "")
            # [CRITICAL UPDATE] Keep 'remix', 'lofi', 'slowed' for accuracy
            return text.strip()
        except: return ""

smart_mix = SmartLoader()
