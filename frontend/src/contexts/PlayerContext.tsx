import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
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
      console.warn("Audio stream notice:", e);
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

      // Connect WebSocket
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${window.location.host}/api/sessions/${sid}/events`;
      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.current) {
              const trk = mapBackendTrack(data.current);
              setCurrentTrack((prev) => (prev?.id === trk.id ? prev : trk));
            }
            if (data.queue) {
              const newQueue = data.queue.map(mapBackendTrack);
              setQueue((prev) => {
                if (prev.length === newQueue.length && prev.every((t, idx) => t.id === newQueue[idx]?.id)) {
                  return prev;
                }
                return newQueue;
              });
            }
            if (data.status) {
              setIsPlaying((prev) => (prev === (data.status === "playing") ? prev : data.status === "playing"));
            }
          } catch (err) {
            console.error("WS parse error:", err);
          }
        };
      } catch (err) {
        console.warn("WebSocket connection notice:", err);
      }
    }

    initSession();

    return () => {
      active = false;
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

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
      audio.load();
    }

    const playPromise = audio.play();
    if (playPromise !== undefined) {
      playPromise.catch((error) => {
        console.warn("Audio playback notice:", error);
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
  }, [showLyrics, currentTrack?.id, sessionId]);

  const updateStateFromSnapshot = (snap: any) => {
    if (!snap) return;
    if (snap.current) {
      const trk = mapBackendTrack(snap.current);
      setCurrentTrack((prev) => (prev?.id === trk.id ? prev : trk));
    }
    if (snap.queue) {
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
  };

  const activeSid = () => sessionIdRef.current || sessionId;

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
  }, [sessionId, currentTrack, queue, shuffle]);

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
  }, [sessionId, currentTrack, queue, progress]);

  const playQuery = async (query: string, playNow = true) => {
    const sid = activeSid();
    if (!sid) return;
    const snap = await apiAddToQueue(sid, query, playNow);
    if (snap) updateStateFromSnapshot(snap);
  };

  const playMood = async (moodId: string, customText?: string) => {
    const sid = activeSid();
    if (!sid) return;
    const snap = await apiPlayMood(sid, moodId, customText, true);
    if (snap) updateStateFromSnapshot(snap);
  };

  const api: PlayerApi = {
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
    playTrack: (t, q) => {
      setCurrentTrack(t);
      setProgress(0);
      lastProgressSec.current = 0;
      setIsPlaying(true);
      if (q && q.length) setQueue(q);
      const sid = activeSid();
      if (sid) {
        apiAddToQueue(sid, (t as any).web_url || t.title + " " + t.artistName, true).then(updateStateFromSnapshot);
      }
    },
    playQuery,
    togglePlay: () => {
      const nextPlaying = !isPlaying;
      setIsPlaying(nextPlaying);
      const sid = activeSid();
      if (sid) {
        if (nextPlaying) {
          apiResume(sid);
        } else {
          apiPause(sid);
        }
      }
    },
    next,
    prev,
    seek: (s) => {
      setProgress(s);
      lastProgressSec.current = Math.floor(s);
      if (audioRef.current) audioRef.current.currentTime = s;
      const sid = activeSid();
      if (sid) apiSeek(sid, Math.floor(s * 1000));
    },
    setVolume: (v) => {
      setVol(v);
      if (v > 0) setMuted(false);
      const sid = activeSid();
      if (sid) apiVolume(sid, v);
    },
    toggleMute: () => setMuted((m) => !m),
    toggleShuffle: () => setShuffle((s) => !s),
    cycleRepeat: () => {
      const nextRep = repeat === "off" ? "all" : repeat === "all" ? "one" : "off";
      setRepeat(nextRep);
      const sid = activeSid();
      if (sid) apiRepeat(sid, nextRep);
    },
    setSpeed,
    toggleLike: (id) => setLiked((l) => ({ ...l, [id]: !l[id] })),
    toggleQueue: () => {
      setShowQueue((s) => !s);
      setShowLyrics(false);
    },
    toggleLyrics: () => {
      setShowLyrics((s) => !s);
      setShowQueue(false);
    },
    toggleFullscreen: () => setFullscreen((f) => !f),
    addToQueue: (t) => {
      setQueue((q) => (q.some((x) => x.id === t.id) ? q : [...q, t]));
      const sid = activeSid();
      if (sid) {
        apiAddToQueue(sid, (t as any).web_url || t.title + " " + t.artistName, false).then(updateStateFromSnapshot);
      }
    },
    removeFromQueue: (id) => {
      setQueue((q) => q.filter((t) => t.id !== id));
      const sid = activeSid();
      if (sid) apiRemoveFromQueue(sid, id);
    },
    playMood,
  };

  return <PlayerContext.Provider value={api}>{children}</PlayerContext.Provider>;
}

export function usePlayer() {
  const ctx = useContext(PlayerContext);
  if (!ctx) throw new Error("usePlayer must be used within PlayerProvider");
  return ctx;
}
