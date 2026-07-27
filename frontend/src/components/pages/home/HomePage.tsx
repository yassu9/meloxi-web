import { HeroBanner } from "@/components/pages/home/HeroBanner";
import { CardGrid, CardRow } from "@/components/cards/CardRow";
import { MusicCard } from "@/components/cards/MusicCard";
import { AlbumCard } from "@/components/cards/AlbumCard";
import { ArtistCard } from "@/components/cards/ArtistCard";
import { PlaylistCard } from "@/components/cards/PlaylistCard";
import { PageTransition } from "@/components/layout/PageTransition";
import { albums, artists, genres, moods, playlists, tracks } from "@/data";
import { Link, useNavigate } from "@tanstack/react-router";
import { usePlayer } from "@/contexts/PlayerContext";

export function HomePage() {
  const navigate = useNavigate();
  const player = usePlayer();

  return (
    <PageTransition>
      <div className="mx-auto max-w-[1800px] px-4 lg:px-8 py-6 space-y-10">
        <HeroBanner />

        <CardRow title="Recently played" action={<Link to="/history" className="text-xs font-semibold text-muted-foreground hover:text-foreground">Show all</Link>}>
          <CardGrid cols={6}>
            {tracks.slice(0, 6).map((t) => <MusicCard key={t.id} track={t} queue={tracks} />)}
          </CardGrid>
        </CardRow>

        <CardRow title="Made for you">
          <CardGrid cols={6}>
            {playlists.slice(0, 6).map((p) => <PlaylistCard key={p.id} playlist={p} />)}
          </CardGrid>
        </CardRow>

        <CardRow title="Trending now">
          <CardGrid cols={6}>
            {[...tracks].sort((a, b) => (b.plays ?? 0) - (a.plays ?? 0)).slice(0, 6).map((t) => <MusicCard key={t.id} track={t} queue={tracks} />)}
          </CardGrid>
        </CardRow>

        <CardRow title="Top albums">
          <CardGrid cols={6}>
            {albums.slice(0, 6).map((a) => <AlbumCard key={a.id} album={a} />)}
          </CardGrid>
        </CardRow>

        <CardRow title="Top artists">
          <CardGrid cols={6}>
            {artists.slice(0, 6).map((a) => <ArtistCard key={a.id} artist={a} />)}
          </CardGrid>
        </CardRow>

        <CardRow title="Browse genres">
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            {genres.map((g) => (
              <button
                key={g.id}
                onClick={() => navigate({ to: "/search" })}
                className="relative aspect-[16/9] overflow-hidden rounded-2xl p-4 text-white font-bold text-lg shadow-card text-left hover:scale-[1.02] transition-transform cursor-pointer"
                style={{ background: `linear-gradient(135deg, ${g.gradient[0]}, ${g.gradient[1]})` }}
              >
                {g.name}
              </button>
            ))}
          </div>
        </CardRow>

        <CardRow title="Moods">
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
            {moods.map((m) => (
              <button
                key={m.id}
                onClick={() => player.playMood(m.id)}
                className="relative aspect-square overflow-hidden rounded-2xl p-4 text-white shadow-card flex flex-col justify-between text-left hover:scale-[1.03] transition-transform cursor-pointer"
                style={{ background: `linear-gradient(135deg, ${m.gradient[0]}, ${m.gradient[1]})` }}
              >
                <div className="text-3xl">{m.emoji}</div>
                <div className="font-bold">{m.name}</div>
              </button>
            ))}
          </div>
        </CardRow>

        <CardRow title="New releases">
          <CardGrid cols={6}>
            {albums.slice(2, 8).map((a) => <AlbumCard key={a.id} album={a} />)}
          </CardGrid>
        </CardRow>
      </div>
    </PageTransition>
  );
}
