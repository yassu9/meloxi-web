"""
Lyrics Resolver for Meloxi.
Combines LrcLib (synced LRC lyrics) and JioSaavn API fallback.
"""

import re
import aiohttp
from typing import Dict, Any, Optional, List
from utils.logger import logger

class LyricsResolver:
    """Fetches plain or timestamped lyrics for tracks."""

    LRCLIB_BASE = "https://lrclib.net/api"

    async def get_lyrics(self, title: str, artist: str = "", duration: int = 0) -> Dict[str, Any]:
        """Fetch lyrics with synced lines if available, fallback to plain text."""
        # 1. Clean query strings
        clean_title = self._clean_title(title)
        clean_artist = artist or ""

        # 2. Try LrcLib Synced/Plain API
        lrclib_data = await self._fetch_lrclib(clean_title, clean_artist, duration)
        if lrclib_data:
            return lrclib_data

        # 3. Fallback: JioSaavn Lyrics API
        saavn_data = await self._fetch_jiosaavn_lyrics(clean_title, clean_artist)
        if saavn_data:
            return saavn_data

        # 4. Fallback default if not found
        return {
            "synced": False,
            "plain": f"Lyrics not available for '{title}'.",
            "lines": [{"time": 0, "text": "Instrumental or lyrics unavailable."}],
            "source": "none"
        }

    async def _fetch_lrclib(self, title: str, artist: str, duration: int) -> Optional[Dict[str, Any]]:
        """Query LRCLIB for synced/plain lyrics."""
        headers = {"User-Agent": "MeloxiMusicApp/1.0"}
        params = {"track_name": title}
        if artist:
            params["artist_name"] = artist
        if duration > 0:
            params["duration"] = str(duration)

        try:
            timeout = aiohttp.ClientTimeout(total=8)
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(headers=headers, timeout=timeout, connector=connector) as session:
                # Direct match GET
                async with session.get(f"{self.LRCLIB_BASE}/get", params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return self._format_lrclib_data(data)

                # Search fallback
                search_params = {"q": f"{title} {artist}".strip()}
                async with session.get(f"{self.LRCLIB_BASE}/search", params=search_params) as resp:
                    if resp.status == 200:
                        results = await resp.json()
                        if results and isinstance(results, list):
                            return self._format_lrclib_data(results[0])
        except Exception as exc:
            logger.debug(f"LrcLib connection error: {exc}")
        return None

    def _format_lrclib_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert LRCLIB payload into Meloxi standard format."""
        synced_lrclib = data.get("syncedLyrics")
        plain_lrclib = data.get("plainLyrics")

        if synced_lrclib:
            parsed_lines = self._parse_lrc(synced_lrclib)
            return {
                "synced": True,
                "plain": plain_lrclib or "\n".join([line["text"] for line in parsed_lines]),
                "lines": parsed_lines,
                "source": "lrclib"
            }
        elif plain_lrclib:
            lines = [{"time": 0, "text": line.strip()} for line in plain_lrclib.splitlines() if line.strip()]
            return {
                "synced": False,
                "plain": plain_lrclib,
                "lines": lines,
                "source": "lrclib"
            }
        return {}

    async def _fetch_jiosaavn_lyrics(self, title: str, artist: str) -> Optional[Dict[str, Any]]:
        """Fallback to JioSaavn API lyrics."""
        try:
            from music.saavn_client import saavn
            search_results = await saavn.search(f"{title} {artist}".strip(), limit=1)
            if not search_results:
                return None
            
            song_id = search_results[0].get("id")
            if not song_id:
                return None

            params = {
                "__call": "lyrics.getLyrics",
                "lyrics_id": song_id,
                "ctx": "web6dot0",
                "api_version": "4",
                "_format": "json"
            }
            lyrics_data = await saavn._get(params)
            if lyrics_data and "lyrics" in lyrics_data:
                raw_html = lyrics_data["lyrics"]
                # Clean html breaks
                clean_text = raw_html.replace("<br/>", "\n").replace("<br>", "\n")
                clean_text = re.sub(r"<[^>]+>", "", clean_text)

                import html
                clean_text = html.unescape(clean_text)
                lines = [{"time": 0, "text": line.strip()} for line in clean_text.splitlines() if line.strip()]
                return {
                    "synced": False,
                    "plain": clean_text,
                    "lines": lines,
                    "source": "jiosaavn"
                }
        except Exception as exc:
            logger.debug(f"JioSaavn lyrics error: {exc}")
        return None

    def _parse_lrc(self, lrc_text: str) -> List[Dict[str, Any]]:
        """Parse [mm:ss.xx] timestamped lines into structured array."""
        lines = []
        pattern = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\](.*)")
        for line in lrc_text.splitlines():
            match = pattern.match(line.strip())
            if match:
                minutes = int(match.group(1))
                seconds = float(match.group(2))
                total_seconds = round(minutes * 60 + seconds, 2)
                text = match.group(3).strip()
                if text:
                    lines.append({"time": total_seconds, "text": text})
        lines.sort(key=lambda x: x["time"])
        return lines

    def _clean_title(self, title: str) -> str:
        """Strip junk like '(Official Audio)' or '[Lyrics]'."""
        title = re.sub(r"[\(\[].*?[\)\]]", "", title)
        junk = ["official video", "official audio", "lyric video", "full song", "hd video", "4k"]
        for j in junk:
            title = re.sub(re.escape(j), "", title, flags=re.IGNORECASE)
        return title.strip()

lyrics_resolver = LyricsResolver()
