import type { Track, LyricLine } from "@/types/music";

export const API_BASE = "";

export function mapBackendTrack(raw: any): Track {
  if (!raw) return null as any;
  
  // Create a deterministic, stable ID to avoid reference instability across state updates
  const stableId =
    raw.id ||
    raw._queue_id ||
    raw._playback_id ||
    (raw.title ? `${raw.title}-${raw.artist || ""}`.replace(/\s+/g, "_") : "track-default");

  return {
    id: String(stableId),
    title: raw.title || "Unknown Track",
    artistId: raw.artistId || (raw.artist ? String(raw.artist) : "unknown"),
    artistName: raw.artist || raw.artistName || "Unknown Artist",
    albumId: raw.albumId || (raw.album ? String(raw.album) : "unknown"),
    albumTitle: raw.album || raw.albumTitle || "Single",
    cover: raw.cover || raw.thumbnail || raw.image || "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=500&q=80",
    duration: typeof raw.duration === "number" && raw.duration > 0 ? raw.duration : 180,
    liked: !!raw.liked,
    _queue_id: raw._queue_id || String(stableId),
    _playback_id: raw._playback_id,
    web_url: raw.web_url || raw.url || raw.webpage_url,
  } as Track & { _queue_id?: string; _playback_id?: string; web_url?: string };
}

export async function searchTracks(query: string, limit = 15): Promise<Track[]> {
  try {
    const res = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(query)}&limit=${limit}`);
    if (!res.ok) return [];
    const data = await res.json();
    const items = data.items || [];
    return items.map(mapBackendTrack);
  } catch (err) {
    console.error("Failed to search tracks:", err);
    return [];
  }
}

export async function createSession(): Promise<{ session_id: string; current: any; queue: any[] }> {
  try {
    const res = await fetch(`${API_BASE}/api/sessions`, { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      return {
        session_id: data.id || data.session_id || "default-session",
        current: data.current,
        queue: data.queue || [],
      };
    }
  } catch (e) {
    console.error("Session creation error:", e);
  }
  return { session_id: "default-session", current: null, queue: [] };
}

export async function fetchSessionState(sessionId: string) {
  try {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`);
    if (res.ok) return await res.json();
  } catch (e) {
    console.error("Fetch session state error:", e);
  }
  return null;
}

export async function apiAddToQueue(sessionId: string, query: string, playNow = true) {
  try {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/queue`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, play_now: playNow }),
    });
    if (res.ok) return await res.json();
  } catch (e) {
    console.error("Add to queue error:", e);
  }
  return null;
}

export async function apiRemoveFromQueue(sessionId: string, queueId: string) {
  try {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/queue/${queueId}`, {
      method: "DELETE",
    });
    if (res.ok) return await res.json();
  } catch (e) {
    console.error("Remove from queue error:", e);
  }
  return null;
}

export async function apiClearQueue(sessionId: string) {
  try {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/queue`, {
      method: "DELETE",
    });
    if (res.ok) return await res.json();
  } catch (e) {
    console.error("Clear queue error:", e);
  }
  return null;
}

export async function apiPause(sessionId: string) {
  try {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/pause`, { method: "POST" });
    if (res.ok) return await res.json();
  } catch (e) {
    console.error("Pause error:", e);
  }
  return null;
}

export async function apiResume(sessionId: string) {
  try {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/resume`, { method: "POST" });
    if (res.ok) return await res.json();
  } catch (e) {
    console.error("Resume error:", e);
  }
  return null;
}

export async function apiNext(sessionId: string) {
  try {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/next`, { method: "POST" });
    if (res.ok) return await res.json();
  } catch (e) {
    console.error("Next track error:", e);
  }
  return null;
}

export async function apiPrevious(sessionId: string) {
  try {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/previous`, { method: "POST" });
    if (res.ok) return await res.json();
  } catch (e) {
    console.error("Previous track error:", e);
  }
  return null;
}

export async function apiVolume(sessionId: string, volume: number) {
  try {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/volume`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ volume }),
    });
    if (res.ok) return await res.json();
  } catch (e) {
    console.error("Volume error:", e);
  }
  return null;
}

export async function apiRepeat(sessionId: string, repeat: "off" | "all" | "one") {
  try {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/repeat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ repeat }),
    });
    if (res.ok) return await res.json();
  } catch (e) {
    console.error("Repeat error:", e);
  }
  return null;
}

export async function apiSeek(sessionId: string, positionMs: number) {
  try {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/seek`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ position_ms: positionMs }),
    });
    if (res.ok) return await res.json();
  } catch (e) {
    console.error("Seek error:", e);
  }
  return null;
}

export async function fetchLyrics(sessionId: string, title?: string, artist?: string): Promise<{ synced?: LyricLine[]; plain?: string }> {
  try {
    const params = new URLSearchParams();
    if (title) params.set("title", title);
    if (artist) params.set("artist", artist);
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/lyrics?${params.toString()}`);
    if (res.ok) return await res.json();
  } catch (e) {
    console.error("Fetch lyrics error:", e);
  }
  return {};
}

export async function fetchMoods() {
  try {
    const res = await fetch(`${API_BASE}/api/moods`);
    if (res.ok) return await res.json();
  } catch (e) {
    console.error("Fetch moods error:", e);
  }
  return { moods: [] };
}

export async function apiPlayMood(sessionId: string, moodId: string, customText?: string, playNow = true) {
  try {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/mood/${moodId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ custom_text: customText, play_now: playNow }),
    });
    if (res.ok) return await res.json();
  } catch (e) {
    console.error("Play mood error:", e);
  }
  return null;
}

export async function fetchProfile(userId = "web_guest") {
  try {
    const res = await fetch(`${API_BASE}/api/profile?user_id=${encodeURIComponent(userId)}`);
    if (res.ok) return await res.json();
  } catch (e) {
    console.error("Fetch profile error:", e);
  }
  return null;
}

export async function fetchLeaderboard() {
  try {
    const res = await fetch(`${API_BASE}/api/leaderboard`);
    if (res.ok) return await res.json();
  } catch (e) {
    console.error("Fetch leaderboard error:", e);
  }
  return { leaderboard: [] };
}

export function getStreamUrl(sessionId: string, playbackId?: string): string {
  const pId = playbackId || "current";
  return `${API_BASE}/api/sessions/${sessionId}/stream?t=${pId}`;
}
