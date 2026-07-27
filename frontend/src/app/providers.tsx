import type { ReactNode } from "react";
import { PlayerProvider } from "@/contexts/PlayerContext";
import { SidebarProvider } from "@/contexts/SidebarContext";

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <SidebarProvider>
      <PlayerProvider>{children}</PlayerProvider>
    </SidebarProvider>
  );
}
