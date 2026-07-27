import { Outlet } from "@tanstack/react-router";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { Player } from "@/components/player/Player";
import { QueuePanel } from "@/components/queue/QueuePanel";
import { LyricsPanel } from "@/components/lyrics/LyricsPanel";

export function AppLayout() {
  return (
    <div className="flex min-h-screen w-full bg-background text-foreground">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header />
        <main className="min-w-0 flex-1 pb-40">
          <Outlet />
        </main>
      </div>
      <QueuePanel />
      <LyricsPanel />
      <Player />
    </div>
  );
}
