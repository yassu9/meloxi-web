import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { usePlayer } from "@/contexts/PlayerContext";
import { lyricsByTrack } from "@/data";
import { cn } from "@/lib/utils";

export function LyricsPanel() {
  const p = usePlayer();
  if (!p.currentTrack) return null;
  const lines = p.lyrics && p.lyrics.length > 0 ? p.lyrics : (lyricsByTrack[p.currentTrack.id] ?? [
    { time: 0, text: "Lyrics for this track are being dynamically resolved..." },
    { time: 4, text: "Enjoy the sound experience." },
  ]);
  const activeIdx = lines.reduce((acc, l, i) => (p.progress >= l.time ? i : acc), 0);

  return (
    <AnimatePresence>
      {p.showLyrics && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 overflow-hidden"
        >
          <div className="absolute inset-0" style={{ backgroundImage: `url(${p.currentTrack.cover})`, backgroundSize: "cover", backgroundPosition: "center", filter: "blur(60px) saturate(160%)", transform: "scale(1.2)" }} />
          <div className="absolute inset-0 bg-background/70" />
          <div className="relative h-full flex flex-col">
            <div className="flex items-center justify-between px-6 py-5">
              <div className="flex items-center gap-3">
                <img src={p.currentTrack.cover} alt="" className="size-12 rounded-xl object-cover shadow-glow" />
                <div>
                  <div className="text-sm font-bold">{p.currentTrack.title}</div>
                  <div className="text-xs text-muted-foreground">{p.currentTrack.artistName}</div>
                </div>
              </div>
              <button onClick={p.toggleLyrics} className="grid size-10 place-items-center rounded-full bg-white/10 hover:bg-white/20"><X className="size-5" /></button>
            </div>
            <div className="flex-1 overflow-y-auto scrollbar-hide">
              <div className="mx-auto max-w-2xl px-6 py-24 space-y-6">
                {lines.map((l, i) => (
                  <motion.p
                    key={i}
                    animate={{ opacity: i === activeIdx ? 1 : 0.35, scale: i === activeIdx ? 1.02 : 1 }}
                    className={cn("text-3xl md:text-4xl font-bold leading-snug tracking-tight text-center transition-all", i === activeIdx && "text-gradient-brand")}
                  >
                    {l.text}
                  </motion.p>
                ))}
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
