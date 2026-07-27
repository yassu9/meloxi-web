import { cn } from "@/lib/utils";

export function Logo({ compact = false, className }: { compact?: boolean; className?: string }) {
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <div className="relative grid size-9 place-items-center rounded-xl bg-gradient-brand shadow-glow">
        <svg viewBox="0 0 24 24" className="size-5 text-white" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
          <path d="M4 18V6l7 3 2-3 7 3v9" />
        </svg>
      </div>
      {!compact && (
        <span className="text-lg font-black tracking-tight">
          Melo<span className="text-gradient-brand">xi</span>
        </span>
      )}
    </div>
  );
}
