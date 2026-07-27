import { motion } from "framer-motion";
import { Play, Pause, SkipBack, SkipForward, Shuffle, Repeat, Repeat1, ListMusic, Mic2, Volume2, VolumeX, Maximize2, Heart, Share2, Download, Laptop2, Gauge } from "lucide-react";
import { usePlayer } from "@/contexts/PlayerContext";
import { formatTime } from "@/utils/format";
import { cn } from "@/lib/utils";
import { Slider } from "@/components/ui/slider";
import { MusicWave } from "./MusicWave";

export function Player() {
  const p = usePlayer();
  const t = p.currentTrack;
  if (!t) return null;
  const duration = t.duration;
  const RepeatIcon = p.repeat === "one" ? Repeat1 : Repeat;

  return (
    <motion.div
      initial={{ y: 100 }}
      animate={{ y: 0 }}
      transition={{ type: "spring", stiffness: 240, damping: 26 }}
      className="fixed bottom-0 left-0 right-0 z-40 px-2 sm:px-4 pb-2 sm:pb-4"
    >
      <div className="mx-auto max-w-[1800px] glass rounded-2xl shadow-card border border-white/10">
        <div className="grid grid-cols-3 items-center gap-3 px-3 sm:px-4 py-3">
          {/* Left — track */}
          <div className="flex min-w-0 items-center gap-3">
            <div
              className={cn(
                "relative size-12 sm:size-14 shrink-0 overflow-hidden rounded-lg sm:rounded-xl bg-surface shadow-glow",
                p.isPlaying && "animate-spin-slow"
              )}
            >
              <img src={t.cover} alt={t.title} className="size-full object-cover" />
            </div>
            <div className="min-w-0 hidden sm:block">
              <div className="truncate text-sm font-semibold">{t.title}</div>
              <div className="truncate text-xs text-muted-foreground">{t.artistName}</div>
            </div>
            <button onClick={() => p.toggleLike(t.id)} className="ml-1 hidden sm:grid size-8 place-items-center rounded-full hover:bg-white/5">
              <Heart className={cn("size-4", p.liked[t.id] ? "fill-primary text-primary" : "text-muted-foreground")} />
            </button>
          </div>

          {/* Center — transport + progress */}
          <div className="flex flex-col items-center gap-1.5">
            <div className="flex items-center gap-1 sm:gap-2">
              <button onClick={p.toggleShuffle} className={cn("grid size-8 place-items-center rounded-full hover:bg-white/5", p.shuffle && "text-primary")}><Shuffle className="size-4" /></button>
              <button onClick={p.prev} className="grid size-9 place-items-center rounded-full hover:bg-white/5"><SkipBack className="size-5 fill-current" /></button>
              <button onClick={p.togglePlay} className="grid size-11 place-items-center rounded-full bg-gradient-brand text-white shadow-glow">
                {p.isPlaying ? <Pause className="size-5 fill-current" /> : <Play className="size-5 fill-current translate-x-0.5" />}
              </button>
              <button onClick={p.next} className="grid size-9 place-items-center rounded-full hover:bg-white/5"><SkipForward className="size-5 fill-current" /></button>
              <button onClick={p.cycleRepeat} className={cn("grid size-8 place-items-center rounded-full hover:bg-white/5", p.repeat !== "off" && "text-primary")}><RepeatIcon className="size-4" /></button>
            </div>
            <div className="hidden sm:flex w-full max-w-xl items-center gap-2 text-[11px] text-muted-foreground tabular-nums">
              <span className="w-10 text-right">{formatTime(p.progress)}</span>
              <Slider
                value={[p.progress]}
                max={duration}
                step={1}
                onValueChange={([v]) => p.seek(v)}
                className="flex-1"
              />
              <span className="w-10">-{formatTime(Math.max(0, duration - p.progress))}</span>
            </div>
          </div>

          {/* Right — extras */}
          <div className="flex items-center justify-end gap-0.5 sm:gap-1">
            <MusicWave className="mr-1 hidden md:flex" />
            <button onClick={p.toggleLyrics} className={cn("hidden md:grid size-8 place-items-center rounded-full hover:bg-white/5", p.showLyrics && "text-primary")}><Mic2 className="size-4" /></button>
            <button onClick={p.toggleQueue} className={cn("hidden md:grid size-8 place-items-center rounded-full hover:bg-white/5", p.showQueue && "text-primary")}><ListMusic className="size-4" /></button>
            <button className="hidden lg:grid size-8 place-items-center rounded-full hover:bg-white/5"><Laptop2 className="size-4" /></button>
            <div className="hidden md:flex items-center gap-1 pl-1">
              <button onClick={p.toggleMute} className="grid size-8 place-items-center rounded-full hover:bg-white/5">
                {p.muted || p.volume === 0 ? <VolumeX className="size-4" /> : <Volume2 className="size-4" />}
              </button>
              <Slider value={[p.muted ? 0 : p.volume * 100]} max={100} step={1} onValueChange={([v]) => p.setVolume(v / 100)} className="w-20" />
            </div>
            <button className="hidden lg:grid size-8 place-items-center rounded-full hover:bg-white/5"><Gauge className="size-4" /></button>
            <button className="hidden lg:grid size-8 place-items-center rounded-full hover:bg-white/5"><Share2 className="size-4" /></button>
            <button className="hidden lg:grid size-8 place-items-center rounded-full hover:bg-white/5"><Download className="size-4" /></button>
            <button onClick={p.toggleFullscreen} className="grid size-8 place-items-center rounded-full hover:bg-white/5"><Maximize2 className="size-4" /></button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
