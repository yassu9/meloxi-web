import { Play, Heart, MoreHorizontal, Clock } from "lucide-react";
import { PageTransition } from "@/components/layout/PageTransition";
import { albumById, tracksByIds } from "@/data";
import { usePlayer } from "@/contexts/PlayerContext";
import { formatTime, formatDuration } from "@/utils/format";
import { cn } from "@/lib/utils";
import { Link } from "@tanstack/react-router";

export function AlbumPage({ id }: { id: string }) {
  const album = albumById(id);
  const p = usePlayer();
  if (!album) return <div className="p-10 text-center text-muted-foreground">Album not found.</div>;
  const tracks = tracksByIds(album.trackIds);
  const total = tracks.reduce((s, t) => s + t.duration, 0);

  return (
    <PageTransition>
      <div>
        <div className="relative overflow-hidden bg-gradient-brand-soft">
          <div className="mx-auto max-w-[1800px] px-4 lg:px-8 pt-8 pb-6">
            <div className="grid gap-6 md:grid-cols-[240px_1fr] items-end">
              <img src={album.cover} alt="" className="size-56 md:size-60 rounded-2xl object-cover shadow-glow" />
              <div>
                <div className="text-xs uppercase tracking-widest text-muted-foreground">Album</div>
                <h1 className="mt-2 text-4xl sm:text-5xl md:text-6xl font-black tracking-tight">{album.title}</h1>
                <div className="mt-3 text-sm text-muted-foreground">
                  {album.artistId ? (
                    <Link to="/artist/$id" params={{ id: String(album.artistId) }} className="font-semibold text-foreground hover:underline">{album.artistName}</Link>
                  ) : (
                    <span className="font-semibold text-foreground">{album.artistName}</span>
                  )}
                  {" · "}{album.year} · {tracks.length} songs · {formatDuration(total)}
                </div>
              </div>
            </div>
            <div className="mt-6 flex items-center gap-3">
              <button onClick={() => tracks[0] && p.playTrack(tracks[0], tracks)} className="grid size-14 place-items-center rounded-full bg-gradient-brand text-white shadow-glow hover:scale-105 transition-transform">
                <Play className="size-6 fill-current translate-x-0.5" />
              </button>
              <button className="grid size-11 place-items-center rounded-full hover:bg-white/5"><Heart className="size-5" /></button>
              <button className="grid size-11 place-items-center rounded-full hover:bg-white/5"><MoreHorizontal className="size-5" /></button>
            </div>
          </div>
        </div>

        <div className="mx-auto max-w-[1800px] px-4 lg:px-8 py-4">
          <div className="grid grid-cols-[24px_1fr_60px] gap-4 px-4 py-2 text-xs uppercase tracking-wider text-muted-foreground border-b border-border/50">
            <div>#</div><div>Title</div><div className="text-right"><Clock className="size-4 inline" /></div>
          </div>
          {tracks.map((t, i) => {
            const isCurrent = p.currentTrack?.id === t.id;
            return (
              <button key={t.id} onClick={() => p.playTrack(t, tracks)}
                className={cn("group grid w-full grid-cols-[24px_1fr_60px] gap-4 px-4 py-2.5 items-center rounded-lg hover:bg-white/5 text-left", isCurrent && "bg-white/5")}>
                <div className={cn("text-sm tabular-nums", isCurrent ? "text-primary" : "text-muted-foreground")}>{i + 1}</div>
                <div className="min-w-0">
                  <div className={cn("truncate text-sm", isCurrent ? "text-primary font-semibold" : "font-medium")}>{t.title}</div>
                  <div className="truncate text-xs text-muted-foreground">{t.artistName}</div>
                </div>
                <div className="text-xs text-muted-foreground tabular-nums text-right">{formatTime(t.duration)}</div>
              </button>
            );
          })}
        </div>
      </div>
    </PageTransition>
  );
}
