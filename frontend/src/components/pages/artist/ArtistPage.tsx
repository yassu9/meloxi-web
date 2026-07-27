import { Play, CheckCircle2 } from "lucide-react";
import { PageTransition } from "@/components/layout/PageTransition";
import { CardGrid, CardRow } from "@/components/cards/CardRow";
import { AlbumCard } from "@/components/cards/AlbumCard";
import { ArtistCard } from "@/components/cards/ArtistCard";
import { artistById, artistAlbums, artistTopTracks, relatedArtists } from "@/data";
import { usePlayer } from "@/contexts/PlayerContext";
import { formatCount, formatTime } from "@/utils/format";
import { cn } from "@/lib/utils";

export function ArtistPage({ id }: { id: string }) {
  const artist = artistById(id);
  const p = usePlayer();
  if (!artist) return <div className="p-10 text-center text-muted-foreground">Artist not found.</div>;
  const top = artistTopTracks(id);
  const alb = artistAlbums(id);
  const related = relatedArtists(id);

  return (
    <PageTransition>
      <div>
        <div className="relative h-72 md:h-96 overflow-hidden">
          <img src={artist.banner ?? artist.image} alt="" className="size-full object-cover scale-110 blur-sm" />
          <div className="absolute inset-0 bg-gradient-to-t from-background via-background/60 to-transparent" />
          <div className="absolute inset-x-0 bottom-0 mx-auto max-w-[1800px] px-4 lg:px-8 pb-6">
            <div className="inline-flex items-center gap-2 text-primary text-sm font-semibold"><CheckCircle2 className="size-4 fill-primary text-background" /> Verified Artist</div>
            <h1 className="mt-2 text-5xl md:text-7xl font-black tracking-tight">{artist.name}</h1>
            {artist.monthlyListeners && <div className="mt-2 text-sm text-muted-foreground">{formatCount(artist.monthlyListeners)} monthly listeners</div>}
          </div>
        </div>

        <div className="mx-auto max-w-[1800px] px-4 lg:px-8 py-6 space-y-10">
          <div className="flex items-center gap-3">
            <button onClick={() => top[0] && p.playTrack(top[0], top)} className="grid size-14 place-items-center rounded-full bg-gradient-brand text-white shadow-glow hover:scale-105 transition-transform">
              <Play className="size-6 fill-current translate-x-0.5" />
            </button>
            <button className="rounded-full border border-border px-5 py-2.5 text-sm font-semibold hover:bg-white/5">Follow</button>
          </div>

          <section className="space-y-4">
            <h2 className="text-2xl font-bold">Popular</h2>
            <div>
              {top.slice(0, 5).map((t, i) => {
                const isCurrent = p.currentTrack?.id === t.id;
                return (
                  <button key={t.id} onClick={() => p.playTrack(t, top)}
                    className={cn("group grid w-full grid-cols-[24px_1fr_1fr_60px] gap-4 px-4 py-2.5 items-center rounded-lg hover:bg-white/5 text-left", isCurrent && "bg-white/5")}>
                    <div className={cn("text-sm tabular-nums", isCurrent ? "text-primary" : "text-muted-foreground")}>{i + 1}</div>
                    <div className="flex items-center gap-3 min-w-0">
                      <img src={t.cover} alt="" className="size-10 rounded-md object-cover" />
                      <div className={cn("truncate text-sm", isCurrent ? "text-primary font-semibold" : "font-medium")}>{t.title}</div>
                    </div>
                    <div className="text-xs text-muted-foreground tabular-nums">{formatCount(t.plays ?? 0)}</div>
                    <div className="text-xs text-muted-foreground tabular-nums text-right">{formatTime(t.duration)}</div>
                  </button>
                );
              })}
            </div>
          </section>

          {alb.length > 0 && <CardRow title="Albums"><CardGrid cols={6}>{alb.map((a) => <AlbumCard key={a.id} album={a} />)}</CardGrid></CardRow>}
          {alb.length > 0 && <CardRow title="Singles"><CardGrid cols={6}>{alb.slice(0, 3).map((a) => <AlbumCard key={a.id} album={a} />)}</CardGrid></CardRow>}
          <CardRow title="Fans also like"><CardGrid cols={6}>{related.map((a) => <ArtistCard key={a.id} artist={a} />)}</CardGrid></CardRow>
        </div>
      </div>
    </PageTransition>
  );
}
