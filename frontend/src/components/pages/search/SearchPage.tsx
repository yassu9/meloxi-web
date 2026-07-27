import { useState, useEffect } from "react";
import { Search as SearchIcon, Loader2, X } from "lucide-react";
import { useSearch } from "@tanstack/react-router";
import { PageTransition } from "@/components/layout/PageTransition";
import { CardGrid, CardRow } from "@/components/cards/CardRow";
import { MusicCard } from "@/components/cards/MusicCard";
import { AlbumCard } from "@/components/cards/AlbumCard";
import { ArtistCard } from "@/components/cards/ArtistCard";
import { PlaylistCard } from "@/components/cards/PlaylistCard";
import { albums, artists, playlists, tracks as seedTracks } from "@/data";
import { searchTracks } from "@/lib/api";
import type { Track } from "@/types/music";

const trending = ["Arijit Singh", "Lofi Beats", "Coldplay", "Late night jazz", "Dua Lipa", "Bollywood Top 50"];

export function SearchPage() {
  const searchParams = useSearch({ strict: false }) as { q?: string };
  const initialQ = searchParams?.q || "";

  const [q, setQ] = useState(initialQ);
  const [apiResults, setApiResults] = useState<Track[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (searchParams?.q && searchParams.q !== q) {
      setQ(searchParams.q);
    }
  }, [searchParams?.q]);

  const query = q.trim();

  useEffect(() => {
    if (!query) {
      setApiResults([]);
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await searchTracks(query, 18, controller.signal);
        if (!controller.signal.aborted) {
          setApiResults(res);
        }
      } catch (err: any) {
        if (err?.name !== "AbortError") {
          console.error("Search error:", err);
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }, 300);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
  };

  const match = <T extends { name?: string; title?: string; artistName?: string }>(x: T) =>
    query ? `${x.name ?? ""} ${x.title ?? ""} ${x.artistName ?? ""}`.toLowerCase().includes(query.toLowerCase()) : false;

  const localTracks = query ? seedTracks.filter(match) : seedTracks.slice(0, 12);
  const rawCombined = apiResults.length > 0 ? apiResults : localTracks;

  // Deduplicate tracks safely
  const combinedTracks = rawCombined.filter((t, index, self) =>
    index === self.findIndex((x) => x.id === t.id)
  );

  const rArtists = query ? artists.filter(match) : artists.slice(0, 6);
  const rAlbums = query ? albums.filter(match) : albums.slice(0, 6);
  const rPlaylists = query ? playlists.filter(match) : playlists.slice(0, 6);

  return (
    <PageTransition>
      <div className="mx-auto max-w-[1800px] px-4 lg:px-8 py-6 space-y-8">
        <div className="relative">
          <form onSubmit={handleSubmit} className="glass flex items-center gap-3 rounded-2xl px-5 h-14 border border-white/10 shadow-card focus-within:border-primary/60 transition-colors">
            {loading ? <Loader2 className="size-5 text-primary animate-spin" /> : <SearchIcon className="size-5 text-muted-foreground shrink-0" />}
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search songs, artists, YouTube or JioSaavn links..."
              className="flex-1 bg-transparent outline-none text-base placeholder:text-muted-foreground"
            />
            {q && (
              <button type="button" onClick={() => setQ("")} className="text-muted-foreground hover:text-foreground">
                <X className="size-5" />
              </button>
            )}
          </form>
        </div>

        {!query && (
          <>
            <CardRow title="Trending searches">
              <div className="flex flex-wrap gap-2">
                {trending.map((t) => (
                  <button key={t} type="button" onClick={() => setQ(t)} className="rounded-full bg-surface-2 border border-border px-4 py-2 text-sm hover:bg-surface-3 transition font-medium">
                    {t}
                  </button>
                ))}
              </div>
            </CardRow>
            <CardRow title="Top Categories">
              <div className="flex flex-wrap gap-2">
                {["Hindi Pop", "Punjabi Wave", "EDM Dance", "Ambient Flow", "Rock Classics"].map((t) => (
                  <button key={t} type="button" onClick={() => setQ(t)} className="rounded-full bg-surface-2 border border-border px-4 py-2 text-sm hover:bg-surface-3 transition font-medium">
                    {t}
                  </button>
                ))}
              </div>
            </CardRow>
          </>
        )}

        {combinedTracks.length > 0 && (
          <CardRow title={query ? (apiResults.length > 0 ? `Results for "${query}"` : "Matching Songs") : "Popular Songs"}>
            <CardGrid cols={6}>
              {combinedTracks.map((t) => (
                <MusicCard key={t.id} track={t} queue={combinedTracks} />
              ))}
            </CardGrid>
          </CardRow>
        )}

        {rArtists.length > 0 && (
          <CardRow title="Artists">
            <CardGrid cols={6}>{rArtists.map((a) => <ArtistCard key={a.id} artist={a} />)}</CardGrid>
          </CardRow>
        )}
        {rAlbums.length > 0 && (
          <CardRow title="Albums">
            <CardGrid cols={6}>{rAlbums.map((a) => <AlbumCard key={a.id} album={a} />)}</CardGrid>
          </CardRow>
        )}
        {rPlaylists.length > 0 && (
          <CardRow title="Playlists">
            <CardGrid cols={6}>{rPlaylists.map((p) => <PlaylistCard key={p.id} playlist={p} />)}</CardGrid>
          </CardRow>
        )}
      </div>
    </PageTransition>
  );
}
