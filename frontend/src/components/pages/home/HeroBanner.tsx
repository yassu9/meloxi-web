import { motion } from "framer-motion";
import { Play, Sparkles } from "lucide-react";
import { usePlayer } from "@/contexts/PlayerContext";
import { tracksByIds, playlistById } from "@/data";

export function HeroBanner() {
  const { playTrack } = usePlayer();
  const featured = playlistById("p1")!;
  const tracks = tracksByIds(featured.trackIds);

  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
      className="relative overflow-hidden rounded-3xl shadow-card"
      style={{ background: `linear-gradient(135deg, ${featured.gradient?.[0]}, ${featured.gradient?.[1]})` }}
    >
      <div className="absolute -right-24 -top-24 size-96 rounded-full bg-white/10 blur-3xl" />
      <div className="absolute -left-16 -bottom-24 size-80 rounded-full bg-black/30 blur-3xl" />
      <div className="relative grid gap-8 p-8 sm:p-12 md:grid-cols-[1fr_auto] md:items-end">
        <div className="max-w-2xl text-white">
          <div className="inline-flex items-center gap-2 rounded-full bg-white/15 backdrop-blur px-3 py-1 text-xs font-medium">
            <Sparkles className="size-3.5" /> Featured playlist
          </div>
          <h1 className="mt-4 text-4xl sm:text-5xl md:text-6xl font-black tracking-tight leading-none">{featured.title}</h1>
          <p className="mt-4 text-white/85 text-base sm:text-lg max-w-lg">{featured.description}</p>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button
              onClick={() => tracks[0] && playTrack(tracks[0], tracks)}
              className="inline-flex items-center gap-2 rounded-full bg-white text-black px-6 h-12 font-semibold hover:scale-[1.03] transition-transform"
            >
              <Play className="size-4 fill-current" /> Play now
            </button>
            <button className="inline-flex items-center gap-2 rounded-full border border-white/40 text-white px-6 h-12 font-semibold hover:bg-white/10 transition-colors">
              Save playlist
            </button>
          </div>
        </div>
        <div className="hidden md:block">
          <div className="relative">
            <img src={featured.cover} alt="" className="size-56 rounded-2xl shadow-glow rotate-3" />
          </div>
        </div>
      </div>
    </motion.section>
  );
}
