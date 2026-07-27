import aiohttp
import asyncio
import uuid
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from backend.api.models import AddToQueueRequest, RepeatRequest, VolumeRequest, RadioToggleRequest, MoodPlayRequest, UpdateProfileRequest, ReorderQueueRequest, SeekRequest, MuteRequest
from backend.music.catalog import catalog
from backend.music.lyrics import lyrics_resolver
from backend.music.moods import mood_engine
from backend.services.playback import playback_store

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/search")
async def search(q: str = Query(min_length=1, max_length=500), limit: int = Query(10, ge=1, le=25)):
    return {"items": await catalog.discover(q, limit)}


@router.post("/sessions")
async def create_session():
    session = playback_store.create()
    return playback_store.snapshot(session)


@router.get("/sessions/{session_id}")
async def state(session_id: str):
    return playback_store.snapshot(playback_store.get(session_id))


@router.post("/sessions/{session_id}/queue")
async def add_to_queue(session_id: str, request: AddToQueueRequest):
    is_source_link = request.query.startswith(("http://", "https://"))
    try:
        tracks = await catalog.resolve(request.query, 25 if is_source_link else 1)
    except Exception as exc:
        raise HTTPException(404, f"Could not resolve track: {exc}")
    if not tracks:
        raise HTTPException(404, "No playable track was found")
    session = playback_store.get(session_id)
    async with session.lock:
        for track in tracks:
            track["_queue_id"] = str(uuid.uuid4())
        if request.play_now:
            if session.current:
                session.queue.appendleft(session.current)
            session.current = tracks[0]
            session.current["_playback_id"] = str(uuid.uuid4())
            for track in reversed(tracks[1:]):
                session.queue.appendleft(track)
            session.status = "playing"
        else:
            session.queue.extend(tracks)
    if request.play_now:
        await playback_store.publish(session)
    elif not session.current:
        await playback_store.advance(session)
    else:
        await playback_store.publish(session)
    return playback_store.snapshot(session)


@router.delete("/sessions/{session_id}/queue/{queue_id}")
async def remove_from_queue(session_id: str, queue_id: str):
    session = playback_store.get(session_id)
    if not await playback_store.remove(session, queue_id):
        raise HTTPException(404, "Queue item was not found")
    return playback_store.snapshot(session)


@router.delete("/sessions/{session_id}/queue")
async def clear_queue(session_id: str):
    session = playback_store.get(session_id)
    await playback_store.clear(session)
    return playback_store.snapshot(session)


@router.post("/sessions/{session_id}/stop")
async def stop(session_id: str):
    session = playback_store.get(session_id)
    await playback_store.clear(session, stop=True)
    return playback_store.snapshot(session)


@router.post("/sessions/{session_id}/pause")
async def pause(session_id: str):
    session = playback_store.get(session_id)
    if session.current: session.status = "paused"
    await playback_store.publish(session)
    return playback_store.snapshot(session)


@router.post("/sessions/{session_id}/resume")
async def resume(session_id: str):
    session = playback_store.get(session_id)
    if session.current: session.status = "playing"
    await playback_store.publish(session)
    return playback_store.snapshot(session)


@router.post("/sessions/{session_id}/next")
async def next_track(session_id: str):
    session = playback_store.get(session_id)
    await playback_store.advance(session)
    return playback_store.snapshot(session)


@router.post("/sessions/{session_id}/previous")
async def previous_track(session_id: str):
    session = playback_store.get(session_id)
    await playback_store.advance(session, previous=True)
    return playback_store.snapshot(session)


@router.post("/sessions/{session_id}/shuffle")
async def shuffle(session_id: str):
    session = playback_store.get(session_id)
    await playback_store.shuffle(session)
    return playback_store.snapshot(session)


@router.post("/sessions/{session_id}/volume")
async def volume(session_id: str, request: VolumeRequest):
    session = playback_store.get(session_id)
    vol = int(request.volume * 100) if request.volume <= 1.0 else int(request.volume)
    session.volume = max(0, min(100, vol))
    await playback_store.publish(session)
    return playback_store.snapshot(session)


@router.post("/sessions/{session_id}/repeat")
async def repeat(session_id: str, request: RepeatRequest):
    session = playback_store.get(session_id)
    session.repeat = request.repeat
    await playback_store.publish(session)
    return playback_store.snapshot(session)



@router.post("/sessions/{session_id}/reorder")
async def reorder(session_id: str, request: ReorderQueueRequest):
    session = playback_store.get(session_id)
    if not await playback_store.reorder(session, request.from_index, request.to_index):
        raise HTTPException(400, "Invalid reorder indices")
    return playback_store.snapshot(session)


@router.post("/sessions/{session_id}/seek")
async def seek(session_id: str, request: SeekRequest):
    session = playback_store.get(session_id)
    await playback_store.seek(session, request.position_ms)
    return playback_store.snapshot(session)


@router.post("/sessions/{session_id}/restart")
async def restart(session_id: str):
    session = playback_store.get(session_id)
    await playback_store.restart(session)
    return playback_store.snapshot(session)


@router.post("/sessions/{session_id}/mute")
async def mute(session_id: str, request: MuteRequest):
    session = playback_store.get(session_id)
    await playback_store.set_muted(session, request.muted)
    return playback_store.snapshot(session)


@router.get("/sessions/{session_id}/stream")
async def stream_current(session_id: str, range_header: str | None = Header(default=None, alias="Range")):
    """Proxy source audio so browser CORS and byte-range seeking both work."""
    session = playback_store.get(session_id)
    if not session.current:
        raise HTTPException(409, "Nothing is selected for playback")
    url, req_headers = await catalog.stream_url(session.current)
    if not url:
        raise HTTPException(502, "The selected source could not be resolved")
        
    headers = dict(req_headers)
    if range_header:
        headers["Range"] = range_header

    connector = aiohttp.TCPConnector(ssl=False)
    client = aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=None, sock_connect=20, sock_read=60))
    try:
        response = await client.get(url, headers=headers)
    except aiohttp.ClientError as exc:
        await client.close()
        raise HTTPException(502, f"Audio source could not be reached: {exc}") from exc
    if response.status >= 400:
        response.release(); await client.close()
        raise HTTPException(502, f"Audio source rejected the stream request with HTTP {response.status}")

    forward_headers = {"Accept-Ranges": "bytes", "Cache-Control": "no-store"}
    for header in ("Content-Length", "Content-Range"):
        if value := response.headers.get(header):
            forward_headers[header] = value
    content_type = response.headers.get("Content-Type", "audio/mpeg")

    async def body():
        try:
            async for chunk in response.content.iter_chunked(64 * 1024):
                yield chunk
        finally:
            response.release()
            await client.close()

    return StreamingResponse(body(), status_code=response.status, media_type=content_type, headers=forward_headers)


# ==============================================================================
# 🎵 PHASE 2: LYRICS, MOODS, RADIO & PROFILES
# ==============================================================================

@router.get("/sessions/{session_id}/lyrics")
async def get_lyrics(session_id: str, title: Optional[str] = None, artist: Optional[str] = None):
    """Fetch synced or plain lyrics for currently playing track or custom query."""
    session = playback_store.get(session_id)
    target_title = title or (session.current.get("title") if session.current else None)
    target_artist = artist or (session.current.get("artist") if session.current else "")
    duration = session.current.get("duration", 0) if session.current else 0

    if not target_title:
        raise HTTPException(400, "No track is currently playing and no title was provided")

    return await lyrics_resolver.get_lyrics(target_title, target_artist, duration)


@router.get("/moods")
async def list_moods():
    """List available AI Mood cards and presets."""
    return {"moods": mood_engine.get_moods()}


@router.post("/sessions/{session_id}/mood/{mood_id}")
async def play_mood(session_id: str, mood_id: str, request: Optional[MoodPlayRequest] = None):
    """Play or queue tracks matching AI Mood."""
    custom_text = request.custom_text if request else None
    play_now = request.play_now if request else True

    query = await mood_engine.resolve_mood_query(mood_id, custom_text)
    tracks = await catalog.resolve(query, limit=5)
    if not tracks:
        raise HTTPException(404, f"No tracks found for mood '{mood_id}'")

    session = playback_store.get(session_id)
    async with session.lock:
        for track in tracks:
            track["_queue_id"] = str(uuid.uuid4())
        if play_now:
            if session.current:
                session.queue.appendleft(session.current)
            session.current = tracks[0]
            session.current["_playback_id"] = str(uuid.uuid4())
            for track in reversed(tracks[1:]):
                session.queue.appendleft(track)
            session.status = "playing"
        else:
            session.queue.extend(tracks)

    await playback_store.publish(session)
    return playback_store.snapshot(session)


@router.post("/sessions/{session_id}/radio")
async def toggle_radio(session_id: str, request: RadioToggleRequest):
    """Toggle Auto-DJ Spotify Radio recommendation engine."""
    session = playback_store.get(session_id)
    await playback_store.toggle_radio(session, request.enabled)
    return playback_store.snapshot(session)


@router.get("/profile")
async def get_profile(user_id: str = Query("web_guest")):
    """Get user profile stats, XP, level, and badges."""
    try:
        from database.db import SessionLocal
        from database.models import UserProfile
        db = SessionLocal()
        try:
            profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            if not profile:
                profile = UserProfile(user_id=user_id, xp=0, level=1, bio="Music is my life! 🎧", badges=["Web Pioneer"])
                db.add(profile)
                db.commit()
                db.refresh(profile)

            return {
                "user_id": profile.user_id,
                "xp": profile.xp,
                "level": profile.level,
                "bio": profile.bio,
                "premium": profile.premium,
                "badges": profile.badges or ["Meloxi Listener"],
                "next_level_xp": profile.level * 100
            }
        finally:
            db.close()
    except Exception as exc:
        raise HTTPException(500, f"Profile error: {exc}")


@router.put("/profile")
async def update_profile(request: UpdateProfileRequest):
    """Update user profile bio."""
    try:
        from database.db import SessionLocal
        from database.models import UserProfile
        db = SessionLocal()
        try:
            profile = db.query(UserProfile).filter(UserProfile.user_id == request.user_id).first()
            if profile and request.bio:
                profile.bio = request.bio
                db.commit()
            return {"status": "updated"}
        finally:
            db.close()
    except Exception as exc:
        raise HTTPException(500, f"Profile update error: {exc}")


@router.get("/leaderboard")
async def leaderboard(limit: int = Query(10, ge=1, le=50)):
    """Get top user profiles ranked by XP."""
    try:
        from database.db import SessionLocal
        from database.models import UserProfile
        db = SessionLocal()
        try:
            top_users = db.query(UserProfile).order_by(UserProfile.xp.desc()).limit(limit).all()
            return {
                "leaderboard": [
                    {
                        "user_id": u.user_id,
                        "xp": u.xp,
                        "level": u.level,
                        "bio": u.bio,
                        "badges": u.badges or []
                    }
                    for u in top_users
                ]
            }
        finally:
            db.close()
    except Exception as exc:
        raise HTTPException(500, f"Leaderboard error: {exc}")


@router.websocket("/sessions/{session_id}/events")
async def events(websocket: WebSocket, session_id: str):
    await websocket.accept()
    session = playback_store.get(session_id)
    subscriber = playback_store.subscribe(session_id)
    await websocket.send_json(playback_store.snapshot(session))
    try:
        while True:
            state = await subscriber.get()
            await websocket.send_json(state)
    except (Exception, asyncio.CancelledError, WebSocketDisconnect):
        pass
    finally:
        playback_store.unsubscribe(session_id, subscriber)

