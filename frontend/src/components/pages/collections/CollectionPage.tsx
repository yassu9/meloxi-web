import { PageTransition } from "@/components/layout/PageTransition";
import { CardGrid, CardRow } from "@/components/cards/CardRow";
import { PlaylistCard } from "@/components/cards/PlaylistCard";
import { AlbumCard } from "@/components/cards/AlbumCard";
import { ArtistCard } from "@/components/cards/ArtistCard";
import { MusicCard } from "@/components/cards/MusicCard";
import { albums, artists, playlists, tracks } from "@/data";
import { usePlayer } from "@/contexts/PlayerContext";
import { Heart, Play } from "lucide-react";
import { formatTime } from "@/utils/format";
import type { ReactNode } from "react";

export function CollectionPage({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <PageTransition>
      <div className="mx-auto max-w-[1800px] px-4 lg:px-8 py-6 space-y-6">
        <div>
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight">{title}</h1>
          {subtitle && <p className="mt-2 text-muted-foreground">{subtitle}</p>}
        </div>
        {children}
      </div>
    </PageTransition>
  );
}

export function PlaylistsCollection() {
  return <CollectionPage title="Playlists"><CardGrid cols={6}>{playlists.map((p) => <PlaylistCard key={p.id} playlist={p} />)}</CardGrid></CollectionPage>;
}
export function AlbumsCollection() {
  return <CollectionPage title="Albums"><CardGrid cols={6}>{albums.map((a) => <AlbumCard key={a.id} album={a} />)}</CardGrid></CollectionPage>;
}
export function ArtistsCollection() {
  return <CollectionPage title="Artists"><CardGrid cols={6}>{artists.map((a) => <ArtistCard key={a.id} artist={a} />)}</CardGrid></CollectionPage>;
}
export function HistoryPage() {
  return <CollectionPage title="History" subtitle="Songs you recently played."><CardGrid cols={6}>{tracks.map((t) => <MusicCard key={t.id} track={t} queue={tracks} />)}</CardGrid></CollectionPage>;
}
export function DownloadsPage() {
  return (
    <CollectionPage title="Downloads" subtitle="Available offline.">
      <div className="glass rounded-2xl border border-white/10 p-10 text-center text-muted-foreground">
        Nothing downloaded yet. Tap the download icon on any song or album to save it here.
      </div>
    </CollectionPage>
  );
}
export function LikedSongsPage() {
  const p = usePlayer();
  const liked = tracks.filter((t) => p.liked[t.id]);
  return (
    <CollectionPage title="Liked Songs" subtitle={`${liked.length} songs`}>
      <div className="glass rounded-2xl border border-white/10 overflow-hidden">
        {liked.length === 0 ? (
          <div className="p-10 text-center text-muted-foreground">Songs you like will appear here.</div>
        ) : liked.map((t, i) => (
          <button key={t.id} onClick={() => p.playTrack(t, liked)} className="group w-full flex items-center gap-4 px-5 py-3 hover:bg-white/5 text-left border-b border-border/40 last:border-0">
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
    </CollectionPage>
  );
}

export function ProfilePage() {
  return (
    <PageTransition>
      <div>
        <div className="relative h-64 md:h-80 bg-gradient-brand-soft">
          <div className="absolute inset-x-0 bottom-0 mx-auto max-w-[1800px] px-4 lg:px-8 pb-6">
            <div className="flex items-end gap-6">
              <div className="size-32 md:size-40 rounded-full bg-gradient-brand shadow-glow grid place-items-center text-4xl font-black text-white">MX</div>
              <div>
                <div className="text-xs uppercase tracking-widest text-muted-foreground">Profile</div>
                <h1 className="mt-1 text-4xl md:text-5xl font-black">Meloxi Listener</h1>
                <div className="mt-2 text-sm text-muted-foreground">12 playlists · 148 followers · 62 following</div>
              </div>
            </div>
          </div>
        </div>
        <div className="mx-auto max-w-[1800px] px-4 lg:px-8 py-6 space-y-10">
          <CardRow title="Your top artists this month"><CardGrid cols={6}>{artists.slice(0, 6).map((a) => <ArtistCard key={a.id} artist={a} />)}</CardGrid></CardRow>
          <CardRow title="Your playlists"><CardGrid cols={6}>{playlists.map((p) => <PlaylistCard key={p.id} playlist={p} />)}</CardGrid></CardRow>
        </div>
      </div>
    </PageTransition>
  );
}
