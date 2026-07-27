"""
Spotify Client for Meloxi.
Handles all interactions with Spotify API for Metadata, Recommendations, and Features.
Preferred "Brain" for the bot.
"""

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import logging
import re
from typing import Optional, List, Dict, Any
from utils.logger import logger
from config.settings import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET

# Silence spotipy internal logger to reduce noise
logging.getLogger('spotipy.client').setLevel(logging.CRITICAL)

class SpotifyClient:
    """
    Wrapper around Spotipy with Meloxi-specific logic.
    Handles Auth, Searching, and Recommendations.
    """
    
    def __init__(self):
        self.client = None
        self._connect()
        
    def _connect(self):
        """Initialize Spotify Client with Credentials."""
        try:
            if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
                logger.warning("Spotify Credentials missing. Spotify Brain will be inactive.")
                return

            auth_manager = SpotifyClientCredentials(
                client_id=SPOTIFY_CLIENT_ID,
                client_secret=SPOTIFY_CLIENT_SECRET
            )
            self.client = spotipy.Spotify(auth_manager=auth_manager)
            logger.info("Spotify Brain Connected Successfully.")
        except Exception as e:
            logger.error(f"Spotify Connection Error: {e}")
            self.client = None

    def is_available(self) -> bool:
        """Check if Spotify client is ready."""
        return self.client is not None

    async def _run_async(self, func, *args, **kwargs):
        """Run blocking function in executor."""
        import asyncio
        import functools
        loop = asyncio.get_running_loop()
        partial = functools.partial(func, *args, **kwargs)
        return await loop.run_in_executor(None, partial)

    async def search_track(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Search for a track and return simplified metadata.
        Returns: {title, artist, album, url, image, popularity, id}
        """
        if not self.is_available(): return None
        
        try:
            # Clean query for better Spotify results
            clean_query = self._clean_query(query)
            if not clean_query:
                return None
            
            def _search():
                results = self.client.search(q=clean_query, limit=1, type="track")
                tracks = results.get("tracks", {}).get("items", [])
                if not tracks: return None
                return self._format_track(tracks[0])

            return await self._run_async(_search)
        except Exception as e:
            if "invalid_client" in str(e).lower() or "401" in str(e):
                self.client = None
                logger.debug(f"Spotify credentials invalid, disabling Spotify client.")
            else:
                logger.debug(f"Spotify Search Error: {e}")
            return None


    async def get_track(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific track ID."""
        if not self.is_available(): return None
        try:
            def _get():
                track = self.client.track(track_id)
                return self._format_track(track)
            return await self._run_async(_get)
        except Exception as e:
            logger.error(f"Spotify Get Track Error: {e}")
            return None

    async def get_recommendations(self, seed_tracks: List[str], limit: int = 5, 
                           target_energy: float = None, target_valence: float = None, 
                           min_popularity: int = 0) -> List[Dict[str, Any]]:
        """
        [DEPRECATED BY SPOTIFY NOV 2024]
        Spotify has removed this endpoint, it will naturally return 404.
        Returns empty list immediately to prevent network calls and log spam.
        """
        return []

    async def get_audio_features(self, track_id: str) -> Optional[Dict[str, Any]]:
        """
        [DEPRECATED BY SPOTIFY NOV 2024]
        Returns None to prevent 404 log spam.
        """
        return None

    async def get_artist_top_tracks(self, artist_id: str, country: str = 'IN') -> List[Dict[str, Any]]:
        """Get top tracks for an artist."""
        if not self.is_available(): return []
        try:
            def _top():
                results = self.client.artist_top_tracks(artist_id, country=country)
                return [self._format_track(t) for t in results.get("tracks", [])]
            return await self._run_async(_top)
        except Exception as e:
            logger.warning(f"Spotify Artist Top Tracks Error: {e}")
            return []

    async def get_related_artists(self, artist_id: str) -> List[Dict[str, Any]]:
        """
        [DEPRECATED BY SPOTIFY NOV 2024]
        Returns empty list to prevent 404 log spam.
        """
        return []

    def parse_link(self, url: str) -> Optional[str]:
        """
        Extract ID from Spotify URL.
        Supported: track, playlist, album, artist
        Returns: Tuple(type, id)
        """
        # Basic regex for spotify links
        pattern = r"spotify\.com\/(track|playlist|album|artist)\/([a-zA-Z0-9]+)"
        match = re.search(pattern, url)
        if match:
            return match.group(1), match.group(2)
        return None, None

    async def get_playlist_tracks(self, playlist_id: str, limit: int = 50) -> List[str]:
        """
        Get list of 'Title - Artist' strings from a playlist.
        """
        if not self.is_available(): return []
        try:
            def _playlist():
                results = self.client.playlist_tracks(playlist_id, limit=limit)
                tracks = []
                for item in results.get("items", []):
                    track = item.get("track")
                    if track:
                        tracks.append(f"{track['name']} - {track['artists'][0]['name']}")
                return tracks
            return await self._run_async(_playlist)
        except Exception as e:
            logger.error(f"Spotify Playlist Error: {e}")
            return []

    async def get_album_tracks(self, album_id: str, limit: int = 50) -> List[str]:
        """Get album tracks in the same form used by the shared resolver."""
        if not self.is_available(): return []
        try:
            def _album():
                results = self.client.album_tracks(album_id, limit=limit)
                return [
                    f"{track['name']} - {track['artists'][0]['name']}"
                    for track in results.get("items", []) if track.get("artists")
                ]
            return await self._run_async(_album)
        except Exception as e:
            logger.error(f"Spotify Album Error: {e}")
            return []

    def _format_track(self, track: Dict) -> Dict[str, Any]:
        """Convert Spotify Payload to Internal Dict."""
        try:
            artist = track["artists"][0]["name"]
            title = track["name"]
            album = track["album"]["name"]
            image = track["album"]["images"][0]["url"] if track["album"]["images"] else None
            url = track["external_urls"]["spotify"]
            
            return {
                "title": title,
                "artist": artist,
                "album": album,
                "display_string": f"{title} - {artist}",
                "search_query": f"{title} {artist} audio",
                "spotify_id": track["id"],
                "spotify_url": url,
                "thumbnail": image,
                "duration_ms": track["duration_ms"],
                "popularity": track["popularity"]
            }
        except Exception:
            return {}

    def _clean_query(self, query: str) -> str:
        """Remove video artifacts for better audio search."""
        junk = ["(Official Video)", "(Lyrical)", "Full Song", "Video", "Audio", "Official"]
        for j in junk:
            query = query.replace(j, "")
            query = query.replace(j.lower(), "")
            query = query.replace(j.upper(), "")
        return query.strip()

# Global Instance
spotify = SpotifyClient()
