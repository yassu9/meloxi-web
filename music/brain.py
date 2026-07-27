"""
Core Logic Orchestrator for Meloxi.
"""

from typing import List, Optional, Deque
from music.metadata import MetadataResolver, SongMetadata
from music.curator import VibeMatcher
from music.ai import AIManager
from utils.logger import logger

class Brain:
    """
    The Brain Component.
    Singleton-like usage recommended.
    """
    
    def __init__(self):
        self.resolver = MetadataResolver()
        self.curator = VibeMatcher()
        
    async def resolve_song(self, query: str) -> SongMetadata:
        """
        Input: Raw Query (e.g. "Tum Hi Ho")
        Output: Canonical Metadata (Movie, Artist, Date)
        """
        return await self.resolver.resolve(query)
        
    async def _is_language_match(self, candidate_str: str, target_lang: str) -> bool:
        """Verify if candidate matches the target language."""
        if not target_lang or target_lang == 'unknown': return True
        
        # Fast rule check first
        from music.metadata import MetadataResolver
        resolver = MetadataResolver()
        meta = await resolver.resolve(candidate_str)
        
        if not meta.language or meta.language == 'unknown': return True # Fail safe
        
        # Simple string compare (e.g., 'hindi' == 'hindi')
        return meta.language.lower() == target_lang.lower()

    async def _run_async(self, func, *args, **kwargs):
        import asyncio
        import functools
        loop = asyncio.get_running_loop()
        partial = functools.partial(func, *args, **kwargs)
        return await loop.run_in_executor(None, partial)

    async def get_next_song(self, current_song: dict, history: Deque[str], mood_context: str = None, anchor_metadata: dict = None, played_history_set: set = None) -> Optional[str]:
        """
        Decide the next song for Auto-DJ.
        Pipeline: 
        1. Context Analysis (Energy/Vibe)
        2. Spotify Recs (Tuned to Context & Anchor)
        3. Brain AI Fallback (GPT)
        4. YouTube Mix Fallback
        """
        if played_history_set is None: played_history_set = set()
        logger.info(f"Brain: Thinking about next song... (Mood: {mood_context})")
        
        # 1. Parse Current Song Context
        current_title = current_song.get("title", "")
        current_artist = current_song.get("artist", "")
        
        # Try to resolve to a clean Metadata object
        query_for_resolution = f"{current_title} - {current_artist}" if current_artist != "Unknown" else current_title
        seed_metadata = await self.resolver.resolve(query_for_resolution)
        history_list = list(history)

        # 2. Spotify Brain Recommendation (Preferred)
        from music.spotify_client import spotify
        import config.settings as settings
        spotify_on = getattr(settings, "SPOTIFY_ENABLED", True)
        
        if spotify_on and spotify.is_available() and query_for_resolution.strip():
            # [CRITICAL] Ensure we use a REAL Spotify ID. 
            # Saavn tracks also have IDs stored in 'mbid', but they will 404 on Spotify.
            seed_id = seed_metadata.mbid if "spotify" in getattr(seed_metadata, "source", "") else None
            
            # If no Spotify ID, search specifically to get one
            if not seed_id:
                track = await spotify.search_track(query_for_resolution)
                if track: seed_id = track.get("spotify_id")
            
            # ⚓ MULTI-SEED LOGIC: Use Recent History + Anchor
            seed_tracks = []
            if seed_id: seed_tracks.append(seed_id)
            
            # Incorporate recent history for better variety (Up to 3 recent unique Spotify IDs)
            # This prevents the "vibe loop" by broadening the seed context.
            history_candidates = list(history)[-5:] # Check last 5 (newest)
            for h_str in reversed(history_candidates):
                if len(seed_tracks) >= 3: break # Limit seeds to 3-5 (Spotify allows max 5)

                h_meta = await self.resolver.resolve(h_str)
                h_id = h_meta.mbid if "spotify" in getattr(h_meta, "source", "") else None
                if h_id and h_id not in seed_tracks:
                    seed_tracks.append(h_id)

            if anchor_metadata:
                a_mbid = anchor_metadata.get('mbid')
                a_source = anchor_metadata.get('source', '')
                if a_mbid and "spotify" in str(a_source):
                    if a_mbid not in seed_tracks and len(seed_tracks) < 5:
                        seed_tracks.append(a_mbid)
            
            logger.info(f"Brain: Using Multi-Seeds ({len(seed_tracks)}) -> Recent Context Depth: {len(history_candidates)}")

            
            if seed_tracks:
                # Use the primary seed (Current) for features, but the Set for Recommendations
                seed_for_features = seed_id or seed_tracks[0]
            
            if seed_id:
                # A. Analyze Context (Vibe Check)
                energy = None
                valence = None
                
                # Use the Current Song for Mood/Feature Analysis (to smooth transitions)
                features = await spotify.get_audio_features(seed_for_features)
                if features:
                    energy = features.get('energy')
                    valence = features.get('valence')
                
                # [STABLE] Default fallback for features if Spotify fails to provide them
                energy = energy if energy is not None else 0.5
                valence = valence if valence is not None else 0.5
                logger.info(f"Brain: Seed Vibe - Energy: {energy}, Valence: {valence}")

                
                # B. Tune for Mood (Strict Lock)
                # If NO mood set, infer it from the seed song (Spotify-like continuity)
                if not mood_context:
                    # 1. Spotify Feature Inference (Deterministic)
                    if energy is not None:
                        if energy > 0.65 and valence > 0.55: mood_context = "party"
                        elif energy < 0.45 and valence < 0.45: mood_context = "sad"
                        elif energy > 0.75: mood_context = "workout"
                        elif energy < 0.55 and valence > 0.55: mood_context = "romantic"
                        
                        if mood_context:
                            logger.info(f"Brain: Feature-Inferred Mood -> {mood_context}")

                    # 2. AI Fallback (Contextual)
                    if not mood_context:
                        ai = AIManager()
                        if ai.is_enabled():
                            analysis = await ai.get_detailed_mood_analysis(current_title, current_artist)
                            mood_context = analysis.get("primary_mood")
                            vibe_context = analysis.get("vibe")
                            energy_val = analysis.get("energy")
                            
                            if mood_context == "unknown": mood_context = None
                            
                            if mood_context:
                                logger.info(f"Brain: AI-Inferred Mood -> {mood_context} | Vibe: {vibe_context} | Energy: {energy_val} (Confidence: {analysis.get('confidence', 0)})")
                                # If vibe is specific (e.g. Sufi), append it to mood for better search
                                if vibe_context and vibe_context != 'unknown':
                                    mood_context = f"{mood_context} {vibe_context}"

                # B. Get Recommendations (Playlist & Artist Radio Logic) 📻
                # Note: Spotify deprecated /recommendations and /audio-features in Nov 2024.
                # NEW STRATEGY: Search for a "[Artist] Mix" or "This Is [Artist]" playlist
                # If that fails, fallback to Artist Top Tracks.
                
                valid_candidates = []
                
                if seed_metadata and getattr(seed_metadata, 'artist', None) and seed_metadata.artist != "Unknown":
                    artist_name = seed_metadata.artist
                    
                    # 1. Try Playlist Radio (Rich Context and Variety)
                    try:
                        # Append context based on mood context if available (or empty)
                        p_query = f"This Is {artist_name}" if "party" not in str(mood_context) else f"{artist_name} Party Mix"
                        
                        # Search for playlist
                        p_search = await self._run_async(spotify.client.search, q=p_query, type='playlist', limit=3)
                        playlists = p_search.get('playlists', {}).get('items', [])
                        if playlists and playlists[0]:
                            import random
                            p_id = playlists[0]['id']
                            p_name = playlists[0]['name']
                            p_tracks = await spotify.get_playlist_tracks(p_id, limit=30)
                            
                            # Filter already played & current song
                            for t_str in p_tracks:
                                if not any(self.curator._is_fuzzy_match(t_str, h) for h in history_list) and \
                                   t_str not in played_history_set and \
                                   not self.curator._is_fuzzy_match(t_str, seed_metadata.display_string) and \
                                   await self._is_language_match(t_str, seed_metadata.language):
                                    valid_candidates.append(t_str)
                            
                            if valid_candidates:
                                selected = random.choice(valid_candidates[:10]) # Pick from top tracks
                                logger.info(f"Brain: Playlist Radio Selection ('{p_name}') -> '{selected}'")
                                return selected
                    except Exception as e:
                        logger.warning(f"Brain: Playlist Radio Failed: {e}")

                    # 2. Try Artist Top Tracks (Spotify API Supported Fallback)
                    try:
                        logger.info(f"Brain: Playlist dry. Pivoting to Artist Top Tracks for '{artist_name}'")
                        artist_search = await self._run_async(spotify.client.search, q=artist_name, type='artist', limit=1)
                        artists = artist_search.get('artists', {}).get('items', [])
                        if artists:
                            a_id = artists[0]['id']
                            top_tracks = await spotify.get_artist_top_tracks(a_id)
                            
                            artist_candidates = []
                            for t in top_tracks:
                                t_str = t['display_string']
                                if not any(self.curator._is_fuzzy_match(t_str, h) for h in history_list) and \
                                   t_str not in played_history_set and \
                                   not self.curator._is_fuzzy_match(t_str, seed_metadata.display_string) and \
                                   await self._is_language_match(t_str, seed_metadata.language):
                                    artist_candidates.append(t_str)
                            
                            if artist_candidates:
                                import random
                                selected = random.choice(artist_candidates[:5]) # Pick from top 5
                                logger.info(f"Brain: Artist Radio Selection -> '{selected}'")
                                return selected
                    except Exception as e:
                        logger.warning(f"Brain: Artist Top Tracks Failed: {e}")

        # 2.5 YouTube Related Integration (Spotify-level accuracy for context)
        # This uses the natural algorithm of YouTube to find what follows
        related_videos = current_song.get('related', [])
        if related_videos:
            logger.info(f"Brain: Analyzing {len(related_videos)} Related Videos...")
            from music.player import validate_audio_source
            
            # Filter for Music and Category
            valid_related = []
            for v in related_videos:
                title = v.get('title', '').lower()
                # Simple music heuristic
                if not any(kw in title for kw in ['official trailer', 'movie review', 'reaction', 'full movie', 'gameplay']):
                    # Better format for curator matching
                    artist = v.get('uploader') or v.get('channel') or "Unknown"
                    v_str = f"{v.get('title')} - {artist}"
                    
                    if not any(self.curator._is_fuzzy_match(v_str, h) for h in history_list) and \
                       v.get('id') not in played_history_set and \
                       await self._is_language_match(v_str, seed_metadata.language):
                        valid_related.append(v_str)
            
            if valid_related:
                import random
                selected = random.choice(valid_related[:5]) # Pick from top 5 related
                logger.info(f"Brain: YouTube Related Selection -> '{selected}'")
                return selected

        # 2.6 Similar Artist Expansion (Variety)
        if seed_metadata and seed_metadata.artist and seed_metadata.artist != "Unknown":
            try:
                # Use Last.fm to find similar artists
                similar_artists = await self.curator.lfm.get_similar_artists(seed_metadata.artist, limit=5)
                if similar_artists:
                    import random
                    target_artist = random.choice(similar_artists)
                    logger.info(f"Brain: Expanding to Similar Artist -> {target_artist}")
                    
                    # Get top track for that artist
                    artist_tracks = await self.curator.lfm.get_artist_top_tracks(target_artist, limit=5)
                    for t_str in artist_tracks:
                        if not any(self.curator._is_fuzzy_match(t_str, h) for h in history_list) and \
                           t_str not in played_history_set and \
                           await self._is_language_match(t_str, seed_metadata.language):
                            logger.info(f"Brain: Similar Artist Selection ({target_artist}) -> '{t_str}'")
                            return t_str
            except Exception as e:
                logger.warning(f"Brain: Similar Artist expansion failed: {e}")

        # 3. AI Fallback: GPT-based Recommendations with Language Lock
        logger.info("Brain: All context-rich methods dried. Using AI fallback.")
        ai = AIManager()
        if ai.is_enabled():
            try:
                query_hint = f"{seed_metadata.title} {seed_metadata.artist}"
                if seed_metadata.language and seed_metadata.language != 'unknown':
                    query_hint += f" ({seed_metadata.language} song)"
                
                ai_suggestions = await ai.suggest_related_songs(query_hint)
                if ai_suggestions:
                    for rec in ai_suggestions:
                        if not any(self.curator._is_fuzzy_match(rec, h) for h in history_list) and \
                           await self._is_language_match(rec, seed_metadata.language):
                            logger.info(f"Brain: AI Selection -> '{rec}'")
                            return rec
            except Exception as e:
                logger.warning(f"Brain: AI Suggestion Failed: {e}")

        # 4. Fallback: Curator / YouTube Mix
        logger.info("Brain: Advanced brains exhausted, trying Curator/YouTube silent fallback...")
        curator_rec = await self.curator.get_recommendations(seed_metadata, history_list)
        if curator_rec:
            return curator_rec
            
        # 5. HARD FALLBACK (Nuclear Option)
        # If everything fails, generate a contextual search query that FORCES the language.
        current_lang = getattr(seed_metadata, 'language', 'hindi').lower() if seed_metadata else 'hindi'
        if current_lang == 'unknown': current_lang = 'hindi'
        
        fallback_artist = seed_metadata.artist if seed_metadata and seed_metadata.artist != "Unknown" else ""
        
        # Diversity Guard for Fallback
        artist_counts = {}
        for h in history_list:
            parts = h.split(" - ")
            if len(parts) > 1:
                a = parts[1].strip().lower()
                artist_counts[a] = artist_counts.get(a, 0) + 1
        
        if fallback_artist and fallback_artist.lower() in artist_counts and artist_counts[fallback_artist.lower()] >= 2:
            query = f"trending {current_lang} songs mix"
        elif fallback_artist:
            query = f"latest songs by {fallback_artist} {current_lang}"
        else:
            query = f"top {current_lang} bollywood hits" if current_lang == 'hindi' else f"latest {current_lang} songs"

        logger.info(f"Brain: All APIs failed. Generating Language-Locked Fallback ({current_lang}): '{query}'")
        return query

    async def get_suggestions(self, server_id: int, current_song: dict, limit: int = 10) -> List[str]:
        """
        Get suggestions, prioritized by Spotify -> Last.fm -> YouTube.
        """
        current_title = current_song.get("title", "")
        current_artist = current_song.get("artist", "")
        
        from music.spotify_client import spotify
        
        # 1. Spotify Recommendations
        if spotify.is_available():
             query = f"{current_title} {current_artist}".strip()
             if not query: return []
             track = await spotify.search_track(query)
             if track and track.get('spotify_id'):
                 try:
                     recs = await spotify.get_recommendations([track['spotify_id']], limit=limit)
                     # Return list of display strings
                     if recs:
                        return [r['display_string'] for r in recs]
                 except Exception:
                     # Fallback silently if Spotify fails (e.g. 404 on seed)
                     pass

        # 2. Last.fm Fallback
        # (Existing logic implies getting queries, but here we can try to return clean titles)
        logger.info(f"Brain: Generating YouTube-only suggestion queries for '{current_title}' (Fallback)")
        
        try:
             queries = [
                 f"more songs like {current_title}",
                 f"best of {current_artist}" if current_artist != "Unknown" else f"{current_title} mix",
                 f"{current_title} official audio",
                 f"latest songs by {current_artist}" if current_artist != "Unknown" else f"trending bollywood songs"
             ]
             return queries[:limit]
        except Exception as e:
            logger.error(f"Brain Suggestion Error: {e}")
            return []

    async def record_play(self, server_id: int, current_song: dict):
        """Record a play in the database."""
        await self._update_history(server_id, current_song, is_skip=False)

    async def record_skip(self, server_id: int, current_song: dict):
        """Record a skip (negative feedback)."""
        await self._update_history(server_id, current_song, is_skip=True)

    async def _update_history(self, server_id: int, cur: dict, is_skip: bool):
        """Offload DB transaction."""
        await self._run_async(self._update_history_sync, server_id, cur, is_skip)

    def _update_history_sync(self, server_id: int, cur: dict, is_skip: bool):
        from database.db import SessionLocal
        from database.models import PlaybackHistory
        from sqlalchemy import and_
        
        title = cur.get("title")
        artist = cur.get("artist")
        if not title or len(title) < 2: return
        
        title = title.lower().strip()
        artist = (artist or "Unknown").lower().strip()

        try:
            with SessionLocal() as session:
                history = session.query(PlaybackHistory).filter(
                    and_(
                        PlaybackHistory.server_id == str(server_id),
                        PlaybackHistory.title == title,
                        PlaybackHistory.artist == artist
                    )
                ).first()
                
                if history:
                    if is_skip: history.skip_count += 1
                    else: history.play_count += 1
                    from datetime import datetime
                    history.last_played = datetime.utcnow()
                else:
                    new_history = PlaybackHistory(
                        server_id=str(server_id),
                        title=title,
                        artist=artist,
                        play_count=0 if is_skip else 1,
                        skip_count=1 if is_skip else 0
                    )
                    session.add(new_history)
                session.commit()
        except Exception as e:
            logger.error(f"Brain DB Error: {e}")

# Global Instance
brain = Brain()
