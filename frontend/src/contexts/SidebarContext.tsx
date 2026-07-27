import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

interface SidebarApi {
  collapsed: boolean;
  toggle: () => void;
  mobileOpen: boolean;
  setMobileOpen: (v: boolean) => void;
}

const Ctx = createContext<SidebarApi | null>(null);

export function SidebarProvider({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const v = typeof window !== "undefined" ? window.localStorage.getItem("meloxi:sidebar") : null;
    if (v === "1") setCollapsed(true);
  }, []);

  const toggle = () => setCollapsed((c) => {
    const nv = !c;
    try { window.localStorage.setItem("meloxi:sidebar", nv ? "1" : "0"); } catch {}
    return nv;
  });

  return <Ctx.Provider value={{ collapsed, toggle, mobileOpen, setMobileOpen }}>{children}</Ctx.Provider>;
}

export function useSidebar() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useSidebar must be used within SidebarProvider");
  return ctx;
}
