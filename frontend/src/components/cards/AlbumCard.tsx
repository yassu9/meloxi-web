import { motion } from "framer-motion";
import { Play } from "lucide-react";
import { Link } from "@tanstack/react-router";
import type { Album } from "@/types/music";
import { tracksByIds } from "@/data";
import { usePlayer } from "@/contexts/PlayerContext";

export function AlbumCard({ album }: { album: Album }) {
  const { playTrack } = usePlayer();
  const tracks = tracksByIds(album.trackIds || []);
  const validAlbumId = album.id ? String(album.id) : null;

  const content = (
    <div className="relative overflow-hidden rounded-2xl bg-surface shadow-card">
      <div className="aspect-square">
        <img src={album.cover} alt={album.title} className="size-full object-cover transition-transform duration-500 group-hover:scale-105" />
      </div>
      <button
        onClick={(e) => { e.preventDefault(); e.stopPropagation(); if (tracks[0]) playTrack(tracks[0], tracks); }}
        className="absolute bottom-3 right-3 grid size-11 place-items-center rounded-full bg-gradient-brand text-white shadow-glow translate-y-3 opacity-0 transition-all duration-300 group-hover:translate-y-0 group-hover:opacity-100"
      >
        <Play className="size-5 fill-current" />
      </button>
    </div>
  );

  return (
    <motion.div whileHover={{ y: -4 }} className="group">
      {validAlbumId ? (
        <Link to="/album/$id" params={{ id: validAlbumId }}>
          {content}
          <div className="pt-3 px-1">
            <div className="truncate text-sm font-semibold">{album.title}</div>
            <div className="mt-0.5 truncate text-xs text-muted-foreground">{album.year} · {album.artistName}</div>
          </div>
        </Link>
      ) : (
        <div>
          {content}
          <div className="pt-3 px-1">
            <div className="truncate text-sm font-semibold">{album.title}</div>
            <div className="mt-0.5 truncate text-xs text-muted-foreground">{album.year} · {album.artistName}</div>
          </div>
        </div>
      )}
    </motion.div>
  );
}
