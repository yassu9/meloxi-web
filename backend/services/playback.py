import asyncio
import random
import time
import uuid
import json
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from utils.logger import logger

@dataclass
class PlaybackSession:
    id: str
    queue: deque[dict[str, Any]] = field(default_factory=deque)
    history: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=50))
    current: dict[str, Any] | None = None
    status: str = "idle"
    volume: int = 70
    muted: bool = False
    previous_volume: int = 70
    position_ms: int = 0
    repeat: str = "off"  # off | track | queue
    radio_enabled: bool = False
    updated_at: float = field(default_factory=time.time)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class PlaybackStore:
    """Persistent & Auto-DJ enabled playback store using SQLite DB."""

    def __init__(self) -> None:
        self._sessions: dict[str, PlaybackSession] = {}
        self._subscribers: dict[str, set[asyncio.Queue]] = {}
        self._init_db()

    def _init_db(self):
        """Ensure database tables exist on startup."""
        try:
            from database.db import init_db
            init_db()
        except Exception as exc:
            logger.debug(f"DB Init Warning: {exc}")

    def get(self, session_id: str) -> PlaybackSession:
        if session_id not in self._sessions:
            session = PlaybackSession(id=session_id)
            self._load_from_db(session)
            self._sessions[session_id] = session
        return self._sessions[session_id]

    def create(self) -> PlaybackSession:
        return self.get(str(uuid.uuid4()))

    def snapshot(self, session: PlaybackSession) -> dict[str, Any]:
        return {
            "id": session.id,
            "current": session.current,
            "queue": list(session.queue),
            "history": list(session.history),
            "status": session.status,
            "volume": session.volume,
            "muted": session.muted,
            "position_ms": session.position_ms,
            "repeat": session.repeat,
            "radio_enabled": session.radio_enabled,
            "updated_at": session.updated_at,
        }

    async def publish(self, session: PlaybackSession) -> None:
        session.updated_at = time.time()
        self._save_to_db(session)
        state = self.snapshot(session)
        for subscriber in self._subscribers.get(session.id, set()).copy():
            if subscriber.full():
                try:
                    subscriber.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            subscriber.put_nowait(state)

    def subscribe(self, session_id: str) -> asyncio.Queue:
        subscriber: asyncio.Queue = asyncio.Queue(maxsize=8)
        self._subscribers.setdefault(session_id, set()).add(subscriber)
        return subscriber

    def unsubscribe(self, session_id: str, subscriber: asyncio.Queue) -> None:
        self._subscribers.get(session_id, set()).discard(subscriber)

    async def advance(self, session: PlaybackSession, previous: bool = False) -> None:
        async with session.lock:
            if previous and session.history:
                if session.current:
                    session.queue.appendleft(session.current)
                session.current = session.history.pop()
            else:
                if session.current:
                    # Award XP for finishing track
                    self._award_xp("web_guest", 10)

                    if session.repeat == "track":
                        session.queue.appendleft(session.current)
                    elif session.repeat == "queue":
                        session.queue.append(session.current)
                    session.history.append(session.current)

                # Auto-DJ Radio Refill if queue empty
                if not session.queue and session.radio_enabled and session.current:
                    await self._refill_radio_recommendations(session)

                session.current = session.queue.popleft() if session.queue else None
                if session.current:
                    session.current["_playback_id"] = str(uuid.uuid4())
            session.status = "playing" if session.current else "idle"
        await self.publish(session)

    async def shuffle(self, session: PlaybackSession) -> None:
        async with session.lock:
            items = list(session.queue)
            random.shuffle(items)
            session.queue = deque(items)
        await self.publish(session)

    async def remove(self, session: PlaybackSession, queue_id: str) -> bool:
        async with session.lock:
            for track in list(session.queue):
                if track.get("_queue_id") == queue_id:
                    session.queue.remove(track)
                    await self.publish(session)
                    return True
        return False

    async def clear(self, session: PlaybackSession, stop: bool = False) -> None:
        async with session.lock:
            session.queue.clear()
            if stop:
                session.current = None
                session.status = "idle"
        await self.publish(session)

    async def toggle_radio(self, session: PlaybackSession, enabled: bool) -> None:
        async with session.lock:
            session.radio_enabled = enabled
            if enabled and not session.queue and session.current:
                await self._refill_radio_recommendations(session)
        await self.publish(session)

    async def reorder(self, session: PlaybackSession, from_index: int, to_index: int) -> bool:
        async with session.lock:
            q_list = list(session.queue)
            if 0 <= from_index < len(q_list) and 0 <= to_index < len(q_list):
                item = q_list.pop(from_index)
                q_list.insert(to_index, item)
                session.queue = deque(q_list)
                await self.publish(session)
                return True
        return False

    async def seek(self, session: PlaybackSession, position_ms: int) -> None:
        async with session.lock:
            session.position_ms = max(0, position_ms)
        await self.publish(session)

    async def restart(self, session: PlaybackSession) -> None:
        async with session.lock:
            session.position_ms = 0
            if session.current:
                session.status = "playing"
        await self.publish(session)

    async def set_muted(self, session: PlaybackSession, muted: bool) -> None:
        async with session.lock:
            session.muted = muted
            if muted:
                session.previous_volume = session.volume
                session.volume = 0
            else:
                session.volume = session.previous_volume if session.previous_volume > 0 else 70
        await self.publish(session)

    async def _refill_radio_recommendations(self, session: PlaybackSession) -> None:
        """Fetch recommended songs based on currently playing track or trending seeds."""
        try:
            from music.curator import VibeMatcher
            from music.metadata import SongMetadata
            from backend.music.catalog import catalog

            current_title = session.current.get("title", "") if session.current else ""
            current_artist = session.current.get("artist", "") if session.current else ""

            history_keys = {
                (h.get("title", "") + " " + h.get("artist", "")).lower()
                for h in list(session.history) + list(session.queue)
                if h and isinstance(h, dict)
            }
            if session.current:
                history_keys.add((current_title + " " + current_artist).lower())

            tracks = []
            if current_title:
                meta = SongMetadata(title=current_title, artist=current_artist)
                history_strs = [f"{h.get('title')} - {h.get('artist')}" for h in session.history if isinstance(h, dict)]
                matcher = VibeMatcher()
                rec_query = await matcher.get_recommendations(meta, history_strs)
                if not rec_query:
                    rec_query = f"{current_artist} similar songs" if current_artist else f"songs like {current_title}"
                fetched = await catalog.discover(rec_query, limit=10)
                if isinstance(fetched, list):
                    for t in fetched:
                        if not isinstance(t, dict): continue
                        t_key = (t.get("title", "") + " " + t.get("artist", "")).lower()
                        if not any(hk in t_key or t_key in hk for hk in history_keys if hk):
                            tracks.append(t)
                            history_keys.add(t_key)
                            if len(tracks) >= 4:
                                break
            
            # Fallback if no current track or insufficient tracks found
            if len(tracks) < 3:
                fallback_query = f"{current_artist} hits" if current_artist else "trending bollywood songs"
                more_tracks = await catalog.discover(fallback_query, limit=10)
                if isinstance(more_tracks, list):
                    for t in more_tracks:
                        if not isinstance(t, dict): continue
                        t_key = (t.get("title", "") + " " + t.get("artist", "")).lower()
                        if not any(hk in t_key or t_key in hk for hk in history_keys if hk):
                            tracks.append(t)
                            history_keys.add(t_key)
                            if len(tracks) >= 4:
                                break

            for t in tracks:
                t["_queue_id"] = str(uuid.uuid4())
                session.queue.append(t)

            if not session.current and session.queue:
                session.current = session.queue.popleft()
                session.current["_playback_id"] = str(uuid.uuid4())
                session.status = "playing"
        except Exception as exc:
            logger.debug(f"Radio recommendation error: {exc}")

    def _award_xp(self, user_id: str, amount: int = 10):
        """Add XP to user profile in database."""
        try:
            from database.db import SessionLocal
            from database.models import UserProfile
            db = SessionLocal()
            try:
                profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
                if not profile:
                    profile = UserProfile(user_id=user_id, xp=0, level=1, bio="Music lover 🎧")
                    db.add(profile)
                
                profile.xp += amount
                # Level formula: level = xp // 100 + 1
                profile.level = (profile.xp // 100) + 1
                db.commit()
            finally:
                db.close()
        except Exception as exc:
            logger.debug(f"XP Award DB Error: {exc}")

    def _save_to_db(self, session: PlaybackSession):
        """Persist session state to SQLite database."""
        try:
            from database.db import SessionLocal
            from database.models import MusicQueue
            db = SessionLocal()
            try:
                # Remove previous persistent queue entries for session
                db.query(MusicQueue).filter(MusicQueue.server_id == session.id).delete()
                
                # Save current & queued tracks
                pos = 0
                if session.current:
                    db.add(MusicQueue(
                        server_id=session.id,
                        title=session.current.get("title", "Unknown"),
                        url=session.current.get("webpage_url") or session.current.get("url", ""),
                        duration=session.current.get("duration", 0),
                        requester_id="web_guest",
                        position=pos
                    ))
                    pos += 1
                for track in session.queue:
                    db.add(MusicQueue(
                        server_id=session.id,
                        title=track.get("title", "Unknown"),
                        url=track.get("webpage_url") or track.get("url", ""),
                        duration=track.get("duration", 0),
                        requester_id="web_guest",
                        position=pos
                    ))
                    pos += 1
                db.commit()
            finally:
                db.close()
        except Exception as exc:
            logger.debug(f"Save state DB error: {exc}")

    def _load_from_db(self, session: PlaybackSession):
        """Load session state from SQLite database on first access."""
        try:
            from database.db import SessionLocal
            from database.models import MusicQueue
            db = SessionLocal()
            try:
                saved = db.query(MusicQueue).filter(MusicQueue.server_id == session.id).order_by(MusicQueue.position).all()
                if saved:
                    # First item is current/next
                    session.queue.clear()
                    from backend.music.catalog import catalog
                    for item in saved:
                        session.queue.append({
                            "title": item.title,
                            "url": item.url,
                            "webpage_url": item.url,
                            "duration": item.duration or 0,
                            "_queue_id": str(uuid.uuid4())
                        })
            finally:
                db.close()
        except Exception as exc:
            logger.debug(f"Load state DB error: {exc}")


playback_store = PlaybackStore()
