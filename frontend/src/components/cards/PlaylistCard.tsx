import { motion } from "framer-motion";
import { Play } from "lucide-react";
import { Link } from "@tanstack/react-router";
import type { Playlist } from "@/types/music";
import { tracksByIds } from "@/data";
import { usePlayer } from "@/contexts/PlayerContext";

export function PlaylistCard({ playlist }: { playlist: Playlist }) {
  const { playTrack } = usePlayer();
  const tracks = tracksByIds(playlist.trackIds);
  const [c1, c2] = playlist.gradient ?? ["#7c3aed", "#22d3ee"];

  return (
    <motion.div whileHover={{ y: -4 }} className="group">
      <Link to="/playlist/$id" params={{ id: playlist.id }}>
        <div
          className="relative overflow-hidden rounded-2xl shadow-card p-4 flex flex-col justify-between aspect-square"
          style={{ background: `linear-gradient(135deg, ${c1}, ${c2})` }}
        >
          <div>
            <div className="text-xs uppercase tracking-widest text-white/80">Playlist</div>
            <div className="mt-1 text-xl font-black text-white leading-tight line-clamp-3">{playlist.title}</div>
          </div>
          <div className="text-xs text-white/80 line-clamp-2">{playlist.description}</div>
          <button
            onClick={(e) => { e.preventDefault(); if (tracks[0]) playTrack(tracks[0], tracks); }}
            className="absolute bottom-3 right-3 grid size-11 place-items-center rounded-full bg-black/40 backdrop-blur text-white shadow-glow translate-y-3 opacity-0 transition-all duration-300 group-hover:translate-y-0 group-hover:opacity-100"
          >
            <Play className="size-5 fill-current" />
          </button>
        </div>
      </Link>
    </motion.div>
  );
}
