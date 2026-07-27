"""
Metadata Enrichment for Meloxi.
"""

import re
import asyncio
import urllib.parse
import aiohttp
from difflib import SequenceMatcher
from typing import Optional, List, Dict
from dataclasses import dataclass, field

from utils.logger import logger
from music.saavn_client import saavn
from music.ai import AIManager
ai = AIManager()

# ==============================================================================
# 📦 DATA STRUCTURES
# ==============================================================================

@dataclass
class SongMetadata:
    """Canonical representation of a song."""
    title: str
    artist: str
    album: Optional[str] = None
    release_year: Optional[str] = None
    mbid: Optional[str] = None
    duration: Optional[int] = None # Duration in milliseconds
    thumbnail: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    language: Optional[str] = None
    source: str = "unknown" # 'musicbrainz', 'youtube_parse', 'fallback'
    
    @property
    def display_string(self) -> str:
        """Formatted string for UI."""
        s = f"{self.title} - {self.artist}"
        if self.album: s += f" ({self.album})"
        return s

    @property
    def search_query(self) -> str:
        """Optimized query string for YouTube search."""
        # "Song Title Artist" (Removing 'Unknown' placeholders)
        parts = [self.title]
        if self.artist and "Unknown" not in self.artist:
            parts.append(self.artist)
        
        return " ".join(parts)

# ==============================================================================
# 🧠 MUSICBRAINZ CLIENT
# ==============================================================================

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

# ==============================================================================
# 🧩 METADATA RESOLVER
# ==============================================================================

class MetadataResolver:
    """
    Intelligent Metadata Extractor.
    Pipeline: Spotify (Brain) -> MusicBrainz -> Regex Parsing -> Fallback
    """
    
    def __init__(self):
        from music.spotify_client import spotify
        self.spotify = spotify
        
        # Regex Patterns for Bollywood Titles
        # "Song Name | Movie | Artist"
        # "Song Name - Artist | Movie"
        self.patterns = [
            # T-Series Style: "Song: Title | Artist: Name | Movie: Name"
            re.compile(r"Song[:\s]+(?P<title>[^|]+)\|[\s]*Artist[:\s]+(?P<artist>[^|]+)\|?.*", re.IGNORECASE),
            # Standard: "Title - Artist"
            re.compile(r"(?P<title>.+?)\s*-\s*(?P<artist>.+)", re.IGNORECASE),
            # "Title | Artist | Movie"
            re.compile(r"(?P<title>[^|]+)\s*\|\s*(?P<artist>[^|]+)\s*\|\s*(?P<movie>[^|]+)", re.IGNORECASE),
        ]
        
    async def resolve(self, query: str) -> SongMetadata:
        """
        Resolve a raw query (user input or YT title) to canonical metadata.
        Ensures script consistency (Latin vs Devanagari).
        """
        def has_devanagari(text):
            return any('\u0900' <= char <= '\u097F' for char in text)
            
        is_query_latin = not has_devanagari(query)
        
        meta = await self._resolve_internal(query)
        
        if meta:
            # SCRIPT GUARD (100% Accuracy)
            # If user searched in Latin and we got Devanagari, or vice versa
            # and it's a "Best of" match, we might want to preserve the search script
            # for the title if it's more 'real' for the user's context.
            # But the user specifically said "Real language mein title".
            # This means: English Song -> English Title. Hindi Song -> Hindi Title.
            
            # 1. Update Language first
            if not meta.language or meta.language == 'unknown':
                meta.language = await ai.detect_language(meta.title, meta.artist)
            
            # 2. Enforce Script Purity:
            # If language is 'english' but title has Devanagari -> That's an error/translation.
            if meta.language == 'english' and has_devanagari(meta.title):
                # Attempt to find Latin version or fallback to query if it was latin
                logger.info(f"Metadata: Script Mismatch detected for English song. Reverting Devanagari title.")
                if is_query_latin:
                    meta.title = self._clean_query(query)
            
            # If language is 'hindi' but title is ONLY Latin and query was Devanagari -> Keep Devanagari
            if meta.language == 'hindi' and not is_query_latin and not has_devanagari(meta.title):
                # User specifically searched in Hindi, they probably want the Hindi title
                pass 
                
        return meta

    async def _resolve_internal(self, query: str) -> SongMetadata:
        """Internal resolution logic."""
        # 0. Check for Spotify Link
        if "spotify.com" in query:
            link_type, link_id = self.spotify.parse_link(query)
            if link_type == "track" and link_id:
                # Direct Spotify Track Resolution
                track = await self.spotify.get_track(link_id)
            if track:
                return SongMetadata(
                    title=track['title'],
                    artist=track['artist'],
                    album=track['album'],
                    source="spotify_link",
                    mbid=track.get('spotify_id'),
                    thumbnail=track.get('thumbnail')
                )

        # 0.5 Check for JioSaavn Link
        if "jiosaavn.com" in query:
            res = saavn.parse_link(query)
            if res:
                link_type, link_id, slug = res
                if link_type == "song":
                    track = await saavn.get_song(link_id, slug=slug)
                    if track:
                        # [Master Prompt] Use Spotify/YT for Display Metadata ONLY
                        # Flow: Spotify -> YT -> Safe Text
                        display_meta = None
                        if self.spotify.is_available():
                             display_meta = await self.spotify.search_track(f"{track['title']} {track['artist']}")
                        
                        # Step 2: Fallback to YouTube Metadata if Spotify fails
                        if not display_meta:
                             from music.player import MusicPlayer
                             # Helper search to get YT info
                             # (We use a dummy player or just the search method)
                             temp_player = MusicPlayer(0) # Minimal instance
                             yt_results = await temp_player.search_youtube(f"{track['title']} {track['artist']}", limit=1)
                             if yt_results:
                                  display_meta = {
                                      'title': yt_results[0].get('title'),
                                      'artist': yt_results[0].get('artist'),
                                      'thumbnail': yt_results[0].get('thumbnail')
                                  }

                        return SongMetadata(
                            title=display_meta['title'] if display_meta else track['title'],
                            artist=display_meta['artist'] if display_meta else track['artist'],
                            album=display_meta.get('album') if display_meta else track['album'],
                            source="jiosaavn_link",
                            mbid=display_meta.get('spotify_id') if display_meta else track.get('id'),
                            duration=track.get('duration', 0) * 1000, # To MS
                            thumbnail=display_meta.get('thumbnail') if display_meta else None, # [STRICT] No Saavn Thumbnails
                            language=track.get('language')
                        )
                elif link_type in ["album", "playlist"]:
                    # For albums/playlists, we still need Saavn data for bulk, but sanitize for UI
                    data = await saavn.get_album(link_id, slug=slug) if link_type == "album" else await saavn.get_playlist(link_id, slug=slug)
                    if data:
                         return SongMetadata(
                             title=data['title'],
                             artist="Various Artists",
                             source=f"jiosaavn_{link_type}",
                             mbid=link_id,
                             display_string=slug, 
                             thumbnail=None # [STRICT] No Saavn Thumbnails
                         )
        
        query_clean = self._clean_query(query)
        
        # 1. Try Spotify Search (The Brain)
        if self.spotify.is_available():
            # If query is very short/generic, Spotify might give weird results, but usually it's better.
            track = await self.spotify.search_track(query_clean)
            if track:
                # 🛡️ SIMILARITY GUARD
                # Compare display string with original query. Reject if score < 0.2
                track_str = f"{track['title']} {track['artist']}".lower()
                sim_score = SequenceMatcher(None, query_clean.lower(), track_str).ratio()
                
                if sim_score < 0.2 and len(query_clean) > 5:
                    logger.debug(f"Metadata: Rejecting Spotify result '{track_str}' for query '{query_clean}' (Score: {sim_score:.2f})")
                else:
                    return SongMetadata(
                        title=track['title'],
                        artist=track['artist'],
                        album=track['album'],
                        source="spotify_search",
                        mbid=track.get('spotify_id'),
                        duration=track.get('duration_ms'),
                        thumbnail=track.get('thumbnail')
                    )
        
        # 2. Heuristic Parsing (Fallback)
        parsed = self._parse_regex(query_clean)
        if parsed:
            return parsed
            
        # 3. Try JioSaavn Search (Bollywood/Regional Specialist Backup)
        # User Request: "jio savan optnal he or vo backeup me use kro"
        try:
             results = await saavn.search(query_clean, limit=1)
             if results:
                 track = results[0]
                 return SongMetadata(
                     title=track['title'],
                     artist=track['artist'],
                     album=track['album'],
                     source="jiosaavn_search",
                     mbid=track.get('id'),
                     duration=track.get('duration', 0) * 1000, # To MS
                     thumbnail=track.get('image'),
                     language=track.get('language')
                 )
        except Exception as e:
             logger.error(f"Metadata: Saavn Search Error: {e}")

        # 4. Last Resort
        return SongMetadata(title=query_clean, artist="Unknown (Search)", source="fallback")

    def _parse_regex(self, text: str) -> Optional[SongMetadata]:
        """Attempt to extract metadata via regex."""
        for pattern in self.patterns:
            match = pattern.search(text)
            if match:
                data = match.groupdict()
                title = data.get("title", "").strip()
                artist = data.get("artist", "").strip()
                album = data.get("movie", "").strip()
                
                if title and artist:
                    return SongMetadata(
                        title=title,
                        artist=artist,
                        album=album or None,
                        source="regex_parse"
                    )
        return None

    def _clean_query(self, query: str) -> str:
        """Cleanup junk for better search."""
        if not query: return ""
        junk = ["(Official Video)", "(Lyrical)", "Full Song", "Video", "Audio", "Official"]
        for j in junk:
            query = query.replace(j, "")
            query = query.replace(j.lower(), "")
            query = query.replace(j.upper(), "")
        return query.strip().strip("-|")

