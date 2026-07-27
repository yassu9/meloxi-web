import { motion } from "framer-motion";
import { Play } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { usePlayer } from "@/contexts/PlayerContext";
import type { Track } from "@/types/music";
import { cn } from "@/lib/utils";

interface Props {
  track: Track;
  queue?: Track[];
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function MusicCard({ track, queue, size = "md", className }: Props) {
  const { playTrack, currentTrack, isPlaying } = usePlayer();
  const isCurrent = currentTrack?.id === track.id && isPlaying;
  const validArtistId = track.artistId && track.artistId !== "unknown" ? String(track.artistId) : null;

  return (
    <motion.div whileHover={{ y: -4 }} transition={{ type: "spring", stiffness: 300, damping: 24 }} className={cn("group", className)}>
      <div className="relative overflow-hidden rounded-2xl bg-surface shadow-card">
        <div className="aspect-square">
          <img src={track.cover} alt={track.title} className="size-full object-cover transition-transform duration-500 group-hover:scale-105" />
        </div>
        <button
          onClick={() => playTrack(track, queue)}
          className={cn(
            "absolute bottom-3 right-3 grid size-11 place-items-center rounded-full bg-gradient-brand text-white shadow-glow",
            "translate-y-3 opacity-0 transition-all duration-300 group-hover:translate-y-0 group-hover:opacity-100",
            isCurrent && "translate-y-0 opacity-100",
          )}
          aria-label={`Play ${track.title}`}
        >
          <Play className="size-5 fill-current" />
        </button>
      </div>
      <div className="pt-3 px-1">
        <div className="truncate text-sm font-semibold">{track.title}</div>
        {validArtistId ? (
          <Link to="/artist/$id" params={{ id: validArtistId }} className="mt-0.5 block truncate text-xs text-muted-foreground hover:text-foreground hover:underline">
            {track.artistName}
          </Link>
        ) : (
          <span className="mt-0.5 block truncate text-xs text-muted-foreground">
            {track.artistName}
          </span>
        )}
      </div>
    </motion.div>
  );
}
