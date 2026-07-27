"""Web-safe adapter around Meloxi's existing discovery providers.

Integrated search across JioSaavn, Spotify metadata, and YouTube Music.
"""
import asyncio
import functools
import time
from pathlib import Path
from typing import Any

import yt_dlp

from music.smart_search import smart_mix
from music.saavn_client import saavn

def get_ytdl_options() -> dict[str, Any]:
    opts: dict[str, Any] = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "nocheckcertificate": True,
        "quiet": True,
        "no_warnings": True,
        "default_search": "auto",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "force_ipv4": True,
        "socket_timeout": 15,
        "retries": 3,
        "extractor_args": {"youtube": {"player_client": ["android", "web", "ios"]}},
    }
    cookie_path = Path("cookies.txt")
    if cookie_path.exists() and cookie_path.stat().st_size > 0:
        opts["cookiefile"] = "cookies.txt"
    return opts


class WebCatalog:
    """Find catalogue entries and resolve a playable source for the web app."""

    def __init__(self) -> None:
        self._executor = None

    async def search_youtube(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Adapter method consumed by the existing SmartLoader."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor, functools.partial(self._search_youtube_sync, query, limit)
        )

    def _search_youtube_sync(self, query: str, limit: int) -> list[dict[str, Any]]:
        options = get_ytdl_options()
        options.update({"extract_flat": "in_playlist", "noplaylist": True})
        target = query if query.startswith(("http://", "https://")) else f"ytsearch{limit}:{query}"
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(target, download=False)
        except Exception as exc:
            print(f"[YT-DLP SEARCH WARNING] Search failed for '{query}': {exc}")
            return []
        entries = list(info.get("entries", [])) if info and info.get("entries") else [info]
        candidates = []
        for entry in entries:
            if not entry or not self._is_music_candidate(entry):
                continue
            entry["_quality_score"] = self._quality_score(entry, query)
            candidates.append(entry)
        candidates.sort(key=lambda item: item.get("_quality_score", 0), reverse=True)
        return [self._normalise_youtube(entry) for entry in candidates[:limit]]

    @staticmethod
    def _is_music_candidate(entry: dict[str, Any]) -> bool:
        title = (entry.get("title") or "").lower()
        categories = " ".join(entry.get("categories") or []).lower()
        rejected = ("#shorts", "podcast", "gameplay", "walkthrough", "vlog")
        return not any(word in title or word in categories for word in rejected)

    @staticmethod
    def _quality_score(entry: dict[str, Any], query: str) -> int:
        title = (entry.get("title") or "").lower()
        uploader = (entry.get("uploader") or "").lower()
        score = 100 if query.lower() in title else 0
        if "topic" in uploader: score += 150
        if "vevo" in uploader: score += 80
        if "official audio" in title or "official music video" in title: score += 50
        return score

    @staticmethod
    def _normalise_youtube(entry: dict[str, Any]) -> dict[str, Any]:
        thumbs = [thumb for thumb in entry.get("thumbnails", []) if thumb.get("url")]
        thumbnail = thumbs[-1]["url"] if thumbs else entry.get("thumbnail")
        return {
            "id": entry.get("id"),
            "title": entry.get("title") or "Unknown title",
            "artist": entry.get("artist") or entry.get("uploader") or "Unknown artist",
            "album": entry.get("album"),
            "duration": entry.get("duration") or 0,
            "thumbnail": thumbnail,
            "webpage_url": entry.get("webpage_url") or entry.get("url"),
            "source": "youtube",
        }

    async def discover(self, query: str, limit: int = 15) -> list[dict[str, Any]]:
        """Multi-source search: JioSaavn + Spotify + YouTube Music in parallel."""
        if query.startswith(("http://", "https://")):
            return await self.resolve(query, limit)

        saavn_task = saavn.search(query, limit=limit)
        youtube_task = self.search_youtube(query, limit=limit)
        smart_task = smart_mix.resolve(query, user=None, player=self)

        saavn_res, youtube_res, smart_res = await asyncio.gather(
            saavn_task, youtube_task, smart_task, return_exceptions=True
        )

        saavn_tracks = saavn_res if isinstance(saavn_res, list) else []
        youtube_tracks = youtube_res if isinstance(youtube_res, list) else []
        smart_tracks = smart_res if isinstance(smart_res, list) else []

        merged: list[dict[str, Any]] = []
        seen: set[str] = set()

        for track in [*smart_tracks, *saavn_tracks, *youtube_tracks]:
            if not isinstance(track, dict):
                continue
            title = track.get("title") or ""
            artist = track.get("artist") or ""
            key = f"{title.lower()}-{artist.lower()}".strip("-")
            if key and key not in seen:
                seen.add(key)
                merged.append(track)

        return merged[:limit]

    async def resolve(self, query: str, limit: int = 1) -> list[dict[str, Any]]:
        """Resolve playable track(s) for URLs or search queries."""
        tracks = await smart_mix.resolve(query, user=None, player=self)
        if tracks:
            return tracks[:limit]
        return (await self.search_youtube(query, limit))[:limit]

    async def stream_url(self, track: dict[str, Any]) -> tuple[str | None, dict[str, str]]:
        """Resolve an expiring direct audio URL and HTTP headers when playback begins."""
        cached_url = track.get("_stream_url")
        cached_headers = track.get("_stream_headers", {})
        if cached_url and track.get("_stream_expires_at", 0) > time.time():
            return cached_url, cached_headers

        page_url = track.get("_fallback_webpage_url") or track.get("webpage_url")
        loop = asyncio.get_running_loop()
        stream_url, headers = None, {}

        if page_url and ("youtube.com" in page_url or "youtu.be" in page_url):
            stream_url, headers = await loop.run_in_executor(self._executor, self._stream_url_sync, page_url)

        if not stream_url:
            query = f"{track.get('title', '')} {track.get('artist', '')}".strip()
            if query:
                yt_candidates = await self.search_youtube(query, limit=3)
                for candidate in yt_candidates:
                    cand_url = candidate.get("webpage_url")
                    if cand_url:
                        stream_url, headers = await loop.run_in_executor(self._executor, self._stream_url_sync, cand_url)
                        if stream_url:
                            track["webpage_url"] = cand_url
                            break

        if stream_url:
            track["_stream_url"] = stream_url
            track["_stream_headers"] = headers
            track["_stream_expires_at"] = time.time() + 300
        return stream_url, headers

    @staticmethod
    def _stream_url_sync(page_url: str) -> tuple[str | None, dict[str, str]]:
        options = get_ytdl_options()
        options["extract_flat"] = False
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(page_url, download=False)
            if not info:
                return None, {}
            if info.get("entries"):
                info = next((entry for entry in info["entries"] if entry), {})
            return info.get("url"), info.get("http_headers") or {}
        except Exception as e:
            print(f"[YT-DLP ERROR] Failed to extract info for {page_url}: {e}")
            return None, {}


catalog = WebCatalog()
