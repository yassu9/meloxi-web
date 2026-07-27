import { usePlayer } from "@/contexts/PlayerContext";

export function MusicWave({ bars = 4, className = "" }: { bars?: number; className?: string }) {
  const { isPlaying } = usePlayer();
  return (
    <div className={`flex items-end gap-0.5 h-4 ${className}`}>
      {Array.from({ length: bars }).map((_, i) => (
        <span
          key={i}
          className={`w-0.5 bg-gradient-brand rounded-full ${
            isPlaying ? "animate-wave-bar" : "h-[30%]"
          }`}
          style={{
            animationDelay: isPlaying ? `${i * 0.15}s` : "0s",
            height: isPlaying ? undefined : "30%",
          }}
        />
      ))}
    </div>
  );
}
