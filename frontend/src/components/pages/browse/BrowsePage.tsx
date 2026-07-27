import { PageTransition } from "@/components/layout/PageTransition";
import { CardGrid, CardRow } from "@/components/cards/CardRow";
import { PlaylistCard } from "@/components/cards/PlaylistCard";
import { AlbumCard } from "@/components/cards/AlbumCard";
import { ArtistCard } from "@/components/cards/ArtistCard";
import { MusicCard } from "@/components/cards/MusicCard";
import { albums, artists, genres, moods, playlists, tracks } from "@/data";
import { useNavigate } from "@tanstack/react-router";
import { usePlayer } from "@/contexts/PlayerContext";

export function BrowsePage() {
  const navigate = useNavigate();
  const player = usePlayer();

  return (
    <PageTransition>
      <div className="mx-auto max-w-[1800px] px-4 lg:px-8 py-6 space-y-10">
        <div>
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight">Browse everything</h1>
          <p className="mt-2 text-muted-foreground">Discover new sounds across genres, moods and charts.</p>
        </div>

        <CardRow title="Genres">
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

        <CardRow title="Top charts"><CardGrid cols={6}>{tracks.slice(0, 6).map((t) => <MusicCard key={t.id} track={t} queue={tracks} />)}</CardGrid></CardRow>
        <CardRow title="Featured playlists"><CardGrid cols={6}>{playlists.map((p) => <PlaylistCard key={p.id} playlist={p} />)}</CardGrid></CardRow>
        <CardRow title="Fresh albums"><CardGrid cols={6}>{albums.map((a) => <AlbumCard key={a.id} album={a} />)}</CardGrid></CardRow>
        <CardRow title="Artists to watch"><CardGrid cols={6}>{artists.map((a) => <ArtistCard key={a.id} artist={a} />)}</CardGrid></CardRow>
      </div>
    </PageTransition>
  );
}
