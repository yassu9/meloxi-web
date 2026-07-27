import { AnimatePresence, motion } from "framer-motion";
import { X, GripVertical, Play } from "lucide-react";
import { usePlayer } from "@/contexts/PlayerContext";
import { formatTime } from "@/utils/format";
import { cn } from "@/lib/utils";

export function QueuePanel() {
  const p = usePlayer();
  return (
    <AnimatePresence>
      {p.showQueue && (
        <motion.aside
          initial={{ x: 420, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 420, opacity: 0 }}
          transition={{ type: "spring", stiffness: 260, damping: 30 }}
          className="fixed right-0 top-0 bottom-0 z-40 w-full sm:w-[380px] pt-16 pb-40 pr-2 sm:pr-4"
        >
          <div className="h-full glass rounded-2xl border border-white/10 flex flex-col overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-border/50">
              <h2 className="text-base font-bold">Up next</h2>
              <button onClick={p.toggleQueue} className="grid size-8 place-items-center rounded-full hover:bg-white/5"><X className="size-4" /></button>
            </div>
            {p.currentTrack && (
              <div className="px-5 py-4 border-b border-border/50">
                <div className="text-[11px] uppercase tracking-widest text-muted-foreground mb-2">Now playing</div>
                <div className="flex items-center gap-3">
                  <img src={p.currentTrack.cover} alt="" className="size-12 rounded-lg object-cover" />
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold">{p.currentTrack.title}</div>
                    <div className="truncate text-xs text-muted-foreground">{p.currentTrack.artistName}</div>
                  </div>
                </div>
              </div>
            )}
            <div className="flex-1 overflow-y-auto scrollbar-hide">
              {p.queue.map((t, i) => {
                const isCurrent = t.id === p.currentTrack?.id;
                const uniqueKey = (t as any)._queue_id || `${t.id}-${i}`;
                return (
                  <div key={uniqueKey} className={cn("group flex items-center gap-3 px-5 py-2.5 hover:bg-white/5", isCurrent && "bg-white/5")}>
                    <GripVertical className="size-4 text-muted-foreground opacity-0 group-hover:opacity-100" />
                    <button onClick={() => p.playTrack(t, p.queue)} className="relative size-10 shrink-0 rounded-lg overflow-hidden">
                      <img src={t.cover} alt="" className="size-full object-cover" />
                      <div className="absolute inset-0 grid place-items-center bg-black/50 opacity-0 group-hover:opacity-100"><Play className="size-4 text-white fill-current" /></div>
                    </button>
                    <div className="min-w-0 flex-1">
                      <div className={cn("truncate text-sm", isCurrent ? "font-semibold text-primary" : "font-medium")}>{t.title}</div>
                      <div className="truncate text-xs text-muted-foreground">{t.artistName}</div>
                    </div>
                    <span className="text-xs text-muted-foreground tabular-nums">{formatTime(t.duration)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
