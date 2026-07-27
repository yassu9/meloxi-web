import { useState } from "react";
import { PageTransition } from "@/components/layout/PageTransition";
import { CardGrid, CardRow } from "@/components/cards/CardRow";
import { AlbumCard } from "@/components/cards/AlbumCard";
import { ArtistCard } from "@/components/cards/ArtistCard";
import { PlaylistCard } from "@/components/cards/PlaylistCard";
import { MusicCard } from "@/components/cards/MusicCard";
import { albums, artists, playlists, tracks } from "@/data";
import { usePlayer } from "@/contexts/PlayerContext";
import { formatTime } from "@/utils/format";
import { Heart, Play } from "lucide-react";
import { cn } from "@/lib/utils";

const tabs = ["Liked", "Recent", "Playlists", "Albums", "Artists"] as const;
type Tab = (typeof tabs)[number];

export function LibraryPage() {
  const [tab, setTab] = useState<Tab>("Liked");
  const p = usePlayer();
  const likedTracks = tracks.filter((t) => p.liked[t.id]);

  return (
    <PageTransition>
      <div className="mx-auto max-w-[1800px] px-4 lg:px-8 py-6 space-y-6">
        <div className="flex items-end justify-between">
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight">Your Library</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          {tabs.map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={cn("rounded-full px-4 py-2 text-sm font-semibold border transition-colors",
                tab === t ? "bg-gradient-brand text-white border-transparent shadow-glow" : "bg-surface-2 border-border hover:bg-surface-3")}>
              {t}
            </button>
          ))}
        </div>

        {tab === "Liked" && (
          <div className="glass rounded-2xl border border-white/10 overflow-hidden">
            {likedTracks.length === 0 ? (
              <div className="p-10 text-center text-muted-foreground">No liked songs yet.</div>
            ) : likedTracks.map((t, i) => (
              <button key={t.id} onClick={() => p.playTrack(t, likedTracks)} className="group w-full flex items-center gap-4 px-5 py-3 hover:bg-white/5 text-left border-b border-border/40 last:border-0">
                <div className="w-6 text-sm text-muted-foreground tabular-nums">{i + 1}</div>
                <div className="relative size-10 rounded-lg overflow-hidden">
                  <img src={t.cover} alt="" className="size-full object-cover" />
                  <div className="absolute inset-0 grid place-items-center bg-black/50 opacity-0 group-hover:opacity-100"><Play className="size-4 text-white fill-current" /></div>
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-semibold">{t.title}</div>
                  <div className="truncate text-xs text-muted-foreground">{t.artistName}</div>
                </div>
                <Heart className="size-4 text-primary fill-primary" />
                <span className="text-xs text-muted-foreground tabular-nums w-12 text-right">{formatTime(t.duration)}</span>
              </button>
            ))}
          </div>
        )}

        {tab === "Recent" && <CardRow title="Recently played"><CardGrid cols={6}>{tracks.slice(0, 12).map((t) => <MusicCard key={t.id} track={t} queue={tracks} />)}</CardGrid></CardRow>}
        {tab === "Playlists" && <CardRow title="Your playlists"><CardGrid cols={6}>{playlists.map((p) => <PlaylistCard key={p.id} playlist={p} />)}</CardGrid></CardRow>}
        {tab === "Albums" && <CardRow title="Your albums"><CardGrid cols={6}>{albums.map((a) => <AlbumCard key={a.id} album={a} />)}</CardGrid></CardRow>}
        {tab === "Artists" && <CardRow title="Followed artists"><CardGrid cols={6}>{artists.map((a) => <ArtistCard key={a.id} artist={a} />)}</CardGrid></CardRow>}
      </div>
    </PageTransition>
  );
}
