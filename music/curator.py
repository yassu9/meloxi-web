"""
Curator Engine.
Handles Vibe Matching and Similarity using Last.fm.
"""

import aiohttp
import asyncio
from typing import List, Optional
from utils.logger import logger
from music.metadata import SongMetadata
from config.settings import LASTFM_API_KEY # Needs to be added to settings or env

class LastFMClient:
    """
    Client for Last.fm API.
    """
    BASE_URL = "http://ws.audioscrobbler.com/2.0/"
    
    def __init__(self, api_key: str = None):
        import os
        # 1. Try Env, 2. Arg, 3. Fallback (which is likely dead)
        self.api_key = os.getenv("LASTFM_API_KEY") or api_key or "4fb15509939527f549206353d7110e53"
        
    async def get_similar_tracks(self, artist: str, track: str, limit: int = 10) -> List[str]:
        """Get similar tracks for a song."""
        if not self.api_key: return []

        params = {
            "method": "track.getsimilar",
            "artist": artist,
            "track": track,
            "api_key": self.api_key,
            "format": "json",
            "limit": limit,
            "autocorrect": 1
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        tracks = data.get("similartracks", {}).get("track", [])
                        
                        # Return list of "Title - Artist" strings
                        results = []
                        for t in tracks:
                            name = t.get("name")
                            artist_name = t.get("artist", {}).get("name")
                            if name and artist_name:
                                results.append(f"{name} - {artist_name}")
                        return results
                    elif resp.status == 403:
                         # Silent fail for invalid keys to avoid spam
                         logger.debug("LastFM Key Invalid (403).")
                         return []
                    else:
                        logger.warning(f"LastFM Error: {resp.status}")
                        return []
        except Exception as e:
            logger.debug(f"LastFM Connection Error: {e}") # Debug to reduce noise
            return []

    async def get_similar_artists(self, artist: str, limit: int = 10) -> List[str]:
        """Get similar artists from Last.fm."""
        if not self.api_key: return []

        params = {
            "method": "artist.getsimilar",
            "artist": artist,
            "api_key": self.api_key,
            "format": "json",
            "limit": limit,
            "autocorrect": 1
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        artists = data.get("similarartists", {}).get("artist", [])
                        return [a['name'] for a in artists if 'name' in a]
                    return []
        except Exception:
            return []

    async def get_artist_top_tracks(self, artist: str, limit: int = 10) -> List[str]:
        """Get top tracks for an artist."""
        params = {
            "method": "artist.gettoptracks",
            "artist": artist,
            "api_key": self.api_key,
            "format": "json",
            "limit": limit,
            "autocorrect": 1
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        tracks = data.get("toptracks", {}).get("track", [])
                        return [f"{t['name']} - {artist}" for t in tracks if 'name' in t]
                    return []
        except Exception:
            return []

class VibeMatcher:
    """
    Logic ensuring vibe consistency.
    """
    def __init__(self):
        self.lfm = LastFMClient()
        
    async def get_recommendations(self, seed_metadata: SongMetadata, history: List[str]) -> Optional[str]:
        """
        Get the next best song recommendation.
        Returns a query string "Title - Artist".
        """
        # 0. ALWAYS exclude the seed song itself from being its own recommendation
        seed_str = f"{seed_metadata.title} - {seed_metadata.artist}"
        history.append(seed_str) # Temporarily add to history for filtering
        
        # 1. Try Last.fm Similarity
        if seed_metadata.artist and seed_metadata.title:
            similar = await self.lfm.get_similar_tracks(seed_metadata.artist, seed_metadata.title, limit=15)
            
            # Filter
            for song in similar:
                if not any(self._is_fuzzy_match(song, h) for h in history):
                    return song # Return first valid match
        
        # 2. Fallback: Artist Top Tracks
        if seed_metadata.artist:
             top = await self.lfm.get_artist_top_tracks(seed_metadata.artist, limit=20)
             import random
             random.shuffle(top)
             for song in top:
                if not any(self._is_fuzzy_match(song, h) for h in history):
                    return song

        # 3. Last Resort: Search for "Songs similar to <title>" via YouTube Search Logic
        # This will be handled by the Brain falling back to its own logic if this returns None
        return None

    async def get_similar_tracks_list(self, seed_metadata: SongMetadata, limit: int = 10) -> List[str]:
        """
        Get a list of similar tracks for UI suggestions.
        """
        results = []
        seed_str = f"{seed_metadata.title} - {seed_metadata.artist}"
        
        # 1. Try Last.fm Similarity
        if seed_metadata.artist and seed_metadata.title:
            similar = await self.lfm.get_similar_tracks(seed_metadata.artist, seed_metadata.title, limit=limit + 5)
            results.extend(similar)
            
        # 2. Fallback: Artist Top Tracks
        if len(results) < limit and seed_metadata.artist:
             top = await self.lfm.get_artist_top_tracks(seed_metadata.artist, limit=limit)
             for t in top:
                 if t not in results: results.append(t)

        # Filter out seed song and limit
        final = [r for r in results if not self._is_fuzzy_match(r, seed_str)]
        return final[:limit]

    def _is_fuzzy_match(self, s1: str, s2: str) -> bool:
        """Robust containment and title check for deduplication."""
        if not s1 or not s2: return False
        
        # 1. Normalize and Clean
        def clean(s):
            import re
            s = s.lower().strip()
            # Remove all parentheses and brackets content
            s = re.sub(r'[\(\[].*?[\)\]]', '', s)
            # Remove common music fluff
            junk = [
                "official video", "official audio", "full song", "lyrics", 
                "video song", "audio song", "feat.", "ft.", "produced by", "prod by"
            ]
            for j in junk:
                s = s.replace(j, "")
            
            # Keep only alphanumeric for a "fingerprint"
            return "".join(c for c in s if c.isalnum())
            
        # 2. Extract Titles (if separated by -)
        t1 = s1.split(" - ")[0] if " - " in s1 else s1
        t2 = s2.split(" - ")[0] if " - " in s2 else s2
        
        c1 = clean(t1)
        c2 = clean(t2)
        
        if not c1 or not c2: return False
        
        # 3. Check for high similarity
        # If one fingerprint is a significant part of the other, it's likely a repeat
        if c1 == c2: return True
        if len(c1) > 5 and len(c2) > 5:
            if c1 in c2 or c2 in c1: return True
            
        return False
