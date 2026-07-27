"""
JioSaavn Client for Meloxi.
Handles searching and fetching metadata from JioSaavn public API.
"""

import re
import aiohttp
from typing import Optional, List, Dict, Any
from utils.logger import logger

class SaavnClient:
    """
    Wrapper for JioSaavn API interactions.
    """
    BASE_URL = "https://www.jiosaavn.com/api.php"
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }

    async def _get(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Internal helper for API requests."""
        params.update({
            "_format": "json",
            "_marker": "0",
            "api_version": "4",
            "ctx": "web6dot0"
        })
        
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(headers=self.headers, timeout=timeout, connector=connector) as session:
                async with session.get(self.BASE_URL, params=params) as resp:
                    if resp.status == 200:
                        import json
                        try:
                            # JioSaavn API sometimes returns text/html content type for JSON
                            text = await resp.text()
                            return json.loads(text)
                        except Exception as e:
                            logger.error(f"Failed to parse Saavn JSON: {e}")
                            return None
                    else:
                        logger.warning(f"JioSaavn API Error {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"Saavn API Connection Error: {e}")
            return None

    def parse_link(self, url: str) -> Optional[tuple[str, str, str]]:
        """
        Extract type, token/ID, and slug from JioSaavn URL.
        Supported: song, album, playlist
        """
        patterns = {
            "song": r"jiosaavn\.com\/song\/([^\/]+)\/([a-zA-Z0-9_\-]+)",
            "album": r"jiosaavn\.com\/album\/([^\/]+)\/([a-zA-Z0-9_\-]+)",
            "playlist": r"jiosaavn\.com\/(featured|s\/playlist)\/([^\/]+)\/([a-zA-Z0-9_\-\,]+)"
        }
        
        for k, p in patterns.items():
            match = re.search(p, url)
            if match:
                slug = match.group(1) if k != "playlist" else match.group(2)
                token = match.group(2) if k != "playlist" else match.group(3)
                return k, token, slug.replace("-", " ")
        return None

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for songs."""
        params = {
            "__call": "search.getResults",
            "q": query,
            "n": limit,
            "p": 1
        }
        data = await self._get(params)
        if not data or "results" not in data: return []
        
        return [self._format_track(t) for t in data["results"]]

    async def get_song(self, token: str, slug: str = None) -> Optional[Dict[str, Any]]:
        """Fetch details for a single song. Fallback to search if direct fails."""
        params = {
            "__call": "webapi.get",
            "token": token,
            "type": "song"
        }
        data = await self._get(params)
        # If webapi.get returns song details directly
        if data and "songs" in data and data["songs"]:
            return self._format_track(data["songs"][0])
        
        # Fallback: Search by slug + token hint
        query = slug or token
        results = await self.search(query, limit=5)
        if results:
             # Find best match (ID match preferred, then substring match)
             for r in results:
                 if r.get("id") == token: return r
             for r in results:
                 if slug and slug.lower() in r.get("title", "").lower(): return r
             return results[0]
        return None

    async def get_album(self, token: str, slug: str = None) -> Optional[Dict[str, Any]]:
        """Fetch details for an album and its tracks."""
        params = {
            "__call": "webapi.get",
            "token": token,
            "type": "album"
        }
        data = await self._get(params)
        # Some versions return tracks in 'list', others in 'songs'
        tracks_data = None
        if data:
            tracks_data = data.get("list") or data.get("songs")
        
        if not data or not tracks_data: 
            # Fallback: Search for album
            query = slug or token
            search_results = await self._get({"__call": "search.getAlbumResults", "q": query, "n": 1})
            if search_results and "results" in search_results and search_results["results"]:
                album_id = search_results["results"][0].get("id")
                if album_id:
                    # Try fetching by ID
                    data = await self._get({"__call": "content.getAlbumDetails", "album_id": album_id})
                    if data:
                        tracks_data = data.get("list") or data.get("songs")

        if not data or not tracks_data: return None
        
        album_info = {
            "title": data.get("name") or data.get("title"),
            "artist": data.get("primary_artists") or data.get("subtitle"),
            "image": data.get("image"),
            "tracks": [self._format_track(t) for t in tracks_data]
        }
        return album_info

    async def get_playlist(self, token: str, slug: str = None) -> Optional[Dict[str, Any]]:
        """Fetch details for a playlist and its tracks."""
        params = {
            "__call": "webapi.get",
            "token": token,
            "type": "playlist"
        }
        data = await self._get(params)
        tracks_data = None
        if data:
            tracks_data = data.get("list") or data.get("songs")

        if not data or not tracks_data: return None
        
        playlist_info = {
            "title": data.get("listname") or data.get("title"),
            "image": data.get("image"),
            "tracks": [self._format_track(t) for t in tracks_data]
        }
        return playlist_info

    def _format_track(self, track: Dict) -> Dict[str, Any]:
        """Normalize Saavn payload to Meloxi-friendly dict."""
        try:
            # Duration can be in string or int, check both top-level and more_info
            more_info = track.get("more_info") or {}
            duration = track.get("duration") or more_info.get("duration")
            try:
                duration = int(duration)
                if duration <= 0: duration = 180
            except Exception:
                duration = 180
            
            # Image fix (replace 150x150 with 500x500 for better quality)
            image = track.get("image", "")
            if image:
                # Regex replace any size (50x50, 150x150) with 500x500
                import re
                image = re.sub(r"\d+x\d+", "500x500", image)
            
            return {
                "title": self._unescape(track.get("song") or track.get("title", "Unknown")),
                "artist": self._unescape(track.get("primary_artists") or track.get("subtitle", "Unknown")),
                "album": self._unescape(track.get("album") or "Single"),
                "duration": duration,
                "thumbnail": image,
                "webpage_url": track.get("perma_url"),
                "id": track.get("id"),
                "language": track.get("language", "unknown"),
                "source": "jiosaavn"
            }
        except Exception as e:
            logger.error(f"Saavn Format Error: {e}")
            return {}

    def _unescape(self, text: str) -> str:
        """Fix HTML entities in titles/artists."""
        if not text: return ""
        import html
        return html.unescape(text)

# Global Instance
saavn = SaavnClient()
