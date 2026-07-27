import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { Track, LyricLine } from "@/types/music";
import { tracks as seedTracks } from "@/data";
import {
  createSession,
  apiAddToQueue,
  apiRemoveFromQueue,
  apiPause,
  apiResume,
  apiNext,
  apiPrevious,
  apiVolume,
  apiRepeat,
  apiSeek,
  mapBackendTrack,
  getStreamUrl,
  fetchLyrics,
  apiPlayMood,
} from "@/lib/api";

type Repeat = "off" | "all" | "one";

interface PlayerState {
  sessionId: string;
  currentTrack: Track | null;
  isPlaying: boolean;
  progress: number; // seconds
  volume: number; // 0..1
  muted: boolean;
  shuffle: boolean;
  repeat: Repeat;
  speed: number;
  liked: Record<string, boolean>;
  queue: Track[];
  showQueue: boolean;
  showLyrics: boolean;
  fullscreen: boolean;
  lyrics: LyricLine[];
}

interface PlayerApi extends PlayerState {
  playTrack: (t: Track, queue?: Track[]) => void;
  playQuery: (query: string, playNow?: boolean) => Promise<void>;
  togglePlay: () => void;
  next: () => void;
  prev: () => void;
  seek: (s: number) => void;
  setVolume: (v: number) => void;
  toggleMute: () => void;
  toggleShuffle: () => void;
  cycleRepeat: () => void;
  setSpeed: (s: number) => void;
  toggleLike: (id: string) => void;
  toggleQueue: () => void;
  toggleLyrics: () => void;
  toggleFullscreen: () => void;
  addToQueue: (t: Track) => void;
  removeFromQueue: (id: string) => void;
  playMood: (moodId: string, customText?: string) => Promise<void>;
}

const PlayerContext = createContext<PlayerApi | null>(null);

export function PlayerProvider({ children }: { children: ReactNode }) {
  const [sessionId, setSessionId] = useState<string>("");
  const [currentTrack, setCurrentTrack] = useState<Track | null>(seedTracks[0]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [volume, setVol] = useState(0.8);
  const [muted, setMuted] = useState(false);
  const [shuffle, setShuffle] = useState(false);
  const [repeat, setRepeat] = useState<Repeat>("off");
  const [speed, setSpeed] = useState(1);
  const [liked, setLiked] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(seedTracks.filter((t) => t.liked).map((t) => [t.id, true]))
  );
  const [queue, setQueue] = useState<Track[]>(seedTracks.slice(0, 6));
  const [showQueue, setShowQueue] = useState(false);
  const [showLyrics, setShowLyrics] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [lyrics, setLyrics] = useState<LyricLine[]>([]);

  const sessionIdRef = useRef<string>("");
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const lastProgressSec = useRef<number>(-1);

  // Initialize HTML5 Audio element once
  useEffect(() => {
    const audio = new Audio();
    audio.preload = "none";
    audioRef.current = audio;

    const onTimeUpdate = () => {
      const sec = Math.floor(audio.currentTime);
      if (sec !== lastProgressSec.current) {
        lastProgressSec.current = sec;
        setProgress(sec);
      }
    };

    const onEnded = () => {
      if (repeat === "one") {
        audio.currentTime = 0;
        audio.play().catch(() => {});
      } else {
        next();
      }
    };

    const onError = (e: any) => {
      // Clean safe log without object serialization loops
      if (e && e.type) {
        console.warn("Audio element notice:", e.type);
      }
    };

    audio.addEventListener("timeupdate", onTimeUpdate);
    audio.addEventListener("ended", onEnded);
    audio.addEventListener("error", onError);

    return () => {
      audio.removeEventListener("timeupdate", onTimeUpdate);
      audio.removeEventListener("ended", onEnded);
      audio.removeEventListener("error", onError);
      audio.pause();
    };
  }, [repeat]);

  const activeSid = useCallback(() => sessionIdRef.current || sessionId, [sessionId]);

  const updateStateFromSnapshot = useCallback((snap: any) => {
    if (!snap) return;
    if (snap.current) {
      const trk = mapBackendTrack(snap.current);
      setCurrentTrack((prev) => {
        if (!prev) return trk;
        const isSameTrack = prev.id === trk.id || (prev._queue_id && prev._queue_id === trk._queue_id) || (prev.title === trk.title && prev.artistName === trk.artistName);
        return isSameTrack ? prev : trk;
      });
    }
    if (snap.queue && Array.isArray(snap.queue)) {
      const newQueue = snap.queue.map(mapBackendTrack);
      setQueue((prev) => {
        if (prev.length === newQueue.length && prev.every((t, idx) => t.id === newQueue[idx]?.id)) {
          return prev;
        }
        return newQueue;
      });
    }
    if (snap.status) {
      setIsPlaying((prev) => (prev === (snap.status === "playing") ? prev : snap.status === "playing"));
    }
  }, []);

  // Session & WebSocket Sync
  useEffect(() => {
    let active = true;

    async function initSession() {
      const sessData = await createSession();
      if (!active) return;

      const sid = sessData?.session_id;
      if (!sid) return;

      setSessionId(sid);
      sessionIdRef.current = sid;

      if (sessData.current) {
        const trk = mapBackendTrack(sessData.current);
        setCurrentTrack((prev) => (prev?.id === trk.id ? prev : trk));
      }
      if (sessData.queue && sessData.queue.length > 0) {
        const newQueue = sessData.queue.map(mapBackendTrack);
        setQueue((prev) => {
          if (prev.length === newQueue.length && prev.every((t, idx) => t.id === newQueue[idx]?.id)) {
            return prev;
          }
          return newQueue;
        });
      }

      // Connect WebSocket safely
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${window.location.host}/api/sessions/${sid}/events`;
      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            updateStateFromSnapshot(data);
          } catch (err) {
            console.error("WS parse notice");
          }
        };
      } catch (err) {
        console.warn("WebSocket connection notice");
      }
    }

    initSession();

    return () => {
      active = false;
      if (wsRef.current) wsRef.current.close();
    };
  }, [updateStateFromSnapshot]);

  // Sync volume / muted / rate
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = muted ? 0 : volume;
      audioRef.current.playbackRate = speed;
    }
  }, [volume, muted, speed]);

  // Manage audio stream source stably
  useEffect(() => {
    const audio = audioRef.current;
    const sid = sessionIdRef.current || sessionId;
    if (!audio || !sid || !currentTrack) {
      if (audio) audio.pause();
      return;
    }

    const rawTrack = currentTrack as any;
    if (!isPlaying) {
      audio.pause();
      return;
    }

    const streamPath = getStreamUrl(sid, rawTrack._playback_id || currentTrack.id);
    const targetUrl = new URL(streamPath, window.location.href).href;

    if (audio.src !== targetUrl) {
      audio.src = targetUrl;
    }

    const playPromise = audio.play();
    if (playPromise !== undefined) {
      playPromise.catch(() => {
        // Safe promise catch preventing global exception bubbles
      });
    }
  }, [currentTrack?.id, isPlaying, sessionId]);

  // Fetch lyrics
  useEffect(() => {
    const sid = sessionIdRef.current || sessionId;
    if (showLyrics && currentTrack && sid) {
      fetchLyrics(sid, currentTrack.title, currentTrack.artistName).then((res) => {
        if (res.synced && res.synced.length > 0) {
          setLyrics(res.synced);
        } else if (res.plain) {
          const lines = res.plain.split("\n").map((text, i) => ({ time: i * 4, text }));
          setLyrics(lines);
        } else {
          setLyrics([
            { time: 0, text: "Lyrics for this track are being dynamically resolved..." },
            { time: 5, text: "Enjoy the music." },
          ]);
        }
      });
    }
  }, [showLyrics, currentTrack?.id, currentTrack?.title, currentTrack?.artistName, sessionId]);

  const next = useCallback(async () => {
    const sid = activeSid();
    if (!sid) return;
    const snap = await apiNext(sid);
    if (snap) {
      updateStateFromSnapshot(snap);
    } else {
      if (!currentTrack || queue.length === 0) return;
      const idx = queue.findIndex((t) => t.id === currentTrack.id);
      const nxt = shuffle ? queue[Math.floor(Math.random() * queue.length)] : queue[(idx + 1) % queue.length];
      if (nxt) {
        setCurrentTrack(nxt);
        setProgress(0);
        lastProgressSec.current = 0;
      }
    }
  }, [activeSid, currentTrack, queue, shuffle, updateStateFromSnapshot]);

  const prev = useCallback(async () => {
    const sid = activeSid();
    if (!sid) return;
    const snap = await apiPrevious(sid);
    if (snap) {
      updateStateFromSnapshot(snap);
    } else {
      if (!currentTrack || queue.length === 0) return;
      if (progress > 3 && audioRef.current) {
        audioRef.current.currentTime = 0;
        setProgress(0);
        lastProgressSec.current = 0;
        return;
      }
      const idx = queue.findIndex((t) => t.id === currentTrack.id);
      const prv = queue[(idx - 1 + queue.length) % queue.length];
      if (prv) {
        setCurrentTrack(prv);
        setProgress(0);
        lastProgressSec.current = 0;
      }
    }
  }, [activeSid, currentTrack, queue, progress, updateStateFromSnapshot]);

  const playTrack = useCallback((t: Track, q?: Track[]) => {
    setCurrentTrack(t);
    setProgress(0);
    lastProgressSec.current = 0;
    setIsPlaying(true);
    if (q && q.length) setQueue(q);
    const sid = activeSid();
    if (sid) {
      apiAddToQueue(sid, (t as any).web_url || t.title + " " + t.artistName, true).then(updateStateFromSnapshot);
    }
  }, [activeSid, updateStateFromSnapshot]);

  const playQuery = useCallback(async (query: string, playNow = true) => {
    const sid = activeSid();
    if (!sid) return;
    const snap = await apiAddToQueue(sid, query, playNow);
    if (snap) updateStateFromSnapshot(snap);
  }, [activeSid, updateStateFromSnapshot]);

  const playMood = useCallback(async (moodId: string, customText?: string) => {
    const sid = activeSid();
    if (!sid) return;
    const snap = await apiPlayMood(sid, moodId, customText, true);
    if (snap) updateStateFromSnapshot(snap);
  }, [activeSid, updateStateFromSnapshot]);

  const togglePlay = useCallback(() => {
    setIsPlaying((prevIsPlaying) => {
      const nextPlaying = !prevIsPlaying;
      const sid = activeSid();
      if (sid) {
        if (nextPlaying) {
          apiResume(sid);
        } else {
          apiPause(sid);
        }
      }
      return nextPlaying;
    });
  }, [activeSid]);

  const seek = useCallback((s: number) => {
    setProgress(s);
    lastProgressSec.current = Math.floor(s);
    if (audioRef.current) audioRef.current.currentTime = s;
    const sid = activeSid();
    if (sid) apiSeek(sid, Math.floor(s * 1000));
  }, [activeSid]);

  const setVolume = useCallback((v: number) => {
    setVol(v);
    if (v > 0) setMuted(false);
    const sid = activeSid();
    if (sid) apiVolume(sid, v);
  }, [activeSid]);

  const toggleMute = useCallback(() => setMuted((m) => !m), []);
  const toggleShuffle = useCallback(() => setShuffle((s) => !s), []);
  
  const cycleRepeat = useCallback(() => {
    setRepeat((prevRep) => {
      const nextRep = prevRep === "off" ? "all" : prevRep === "all" ? "one" : "off";
      const sid = activeSid();
      if (sid) apiRepeat(sid, nextRep);
      return nextRep;
    });
  }, [activeSid]);

  const toggleLike = useCallback((id: string) => setLiked((l) => ({ ...l, [id]: !l[id] })), []);
  
  const toggleQueue = useCallback(() => {
    setShowQueue((s) => !s);
    setShowLyrics(false);
  }, []);

  const toggleLyrics = useCallback(() => {
    setShowLyrics((s) => !s);
    setShowQueue(false);
  }, []);

  const toggleFullscreen = useCallback(() => setFullscreen((f) => !f), []);

  const addToQueue = useCallback((t: Track) => {
    setQueue((q) => (q.some((x) => x.id === t.id) ? q : [...q, t]));
    const sid = activeSid();
    if (sid) {
      apiAddToQueue(sid, (t as any).web_url || t.title + " " + t.artistName, false).then(updateStateFromSnapshot);
    }
  }, [activeSid, updateStateFromSnapshot]);

  const removeFromQueue = useCallback((id: string) => {
    setQueue((q) => q.filter((t) => t.id !== id));
    const sid = activeSid();
    if (sid) apiRemoveFromQueue(sid, id);
  }, [activeSid]);

  const api = useMemo<PlayerApi>(() => ({
    sessionId,
    currentTrack,
    isPlaying,
    progress,
    volume,
    muted,
    shuffle,
    repeat,
    speed,
    liked,
    queue,
    showQueue,
    showLyrics,
    fullscreen,
    lyrics,
    playTrack,
    playQuery,
    togglePlay,
    next,
    prev,
    seek,
    setVolume,
    toggleMute,
    toggleShuffle,
    cycleRepeat,
    setSpeed,
    toggleLike,
    toggleQueue,
    toggleLyrics,
    toggleFullscreen,
    addToQueue,
    removeFromQueue,
    playMood,
  }), [
    sessionId,
    currentTrack,
    isPlaying,
    progress,
    volume,
    muted,
    shuffle,
    repeat,
    speed,
    liked,
    queue,
    showQueue,
    showLyrics,
    fullscreen,
    lyrics,
    playTrack,
    playQuery,
    togglePlay,
    next,
    prev,
    seek,
    setVolume,
    toggleMute,
    toggleShuffle,
    cycleRepeat,
    toggleLike,
    toggleQueue,
    toggleLyrics,
    toggleFullscreen,
    addToQueue,
    removeFromQueue,
    playMood,
  ]);

  return <PlayerContext.Provider value={api}>{children}</PlayerContext.Provider>;
}

export function usePlayer() {
  const ctx = useContext(PlayerContext);
  if (!ctx) throw new Error("usePlayer must be used within PlayerProvider");
  return ctx;
}
