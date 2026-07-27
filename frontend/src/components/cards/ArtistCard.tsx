import { motion } from "framer-motion";
import { Link } from "@tanstack/react-router";
import type { Artist } from "@/types/music";
import { formatCount } from "@/utils/format";

export function ArtistCard({ artist }: { artist: Artist }) {
  const validArtistId = artist.id ? String(artist.id) : null;

  const content = (
    <>
      <div className="relative mx-auto aspect-square overflow-hidden rounded-full bg-surface shadow-card">
        <img src={artist.image} alt={artist.name} className="size-full object-cover transition-transform duration-500 group-hover:scale-105" />
      </div>
      <div className="pt-3">
        <div className="truncate text-sm font-semibold">{artist.name}</div>
        {artist.monthlyListeners ? (
          <div className="mt-0.5 text-xs text-muted-foreground">{formatCount(artist.monthlyListeners)} listeners</div>
        ) : null}
      </div>
    </>
  );

  return (
    <motion.div whileHover={{ y: -4 }} className="group text-center">
      {validArtistId ? (
        <Link to="/artist/$id" params={{ id: validArtistId }}>
          {content}
        </Link>
      ) : (
        <div>{content}</div>
      )}
    </motion.div>
  );
}
