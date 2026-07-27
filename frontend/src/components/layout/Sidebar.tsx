import { Link, useRouterState } from "@tanstack/react-router";
import { motion, AnimatePresence } from "framer-motion";
import { Home, Search, Compass, Library, ListMusic, Disc3, Mic2, Heart, History, Download, Settings, User, ChevronLeft, ChevronRight, X } from "lucide-react";
import { useSidebar } from "@/contexts/SidebarContext";
import { cn } from "@/lib/utils";
import { Logo } from "./Logo";

const items = [
  { to: "/", label: "Home", icon: Home },
  { to: "/search", label: "Search", icon: Search },
  { to: "/browse", label: "Browse", icon: Compass },
  { to: "/library", label: "Library", icon: Library },
  { to: "/playlists", label: "Playlists", icon: ListMusic },
  { to: "/albums", label: "Albums", icon: Disc3 },
  { to: "/artists", label: "Artists", icon: Mic2 },
  { to: "/liked", label: "Liked Songs", icon: Heart },
  { to: "/history", label: "History", icon: History },
  { to: "/downloads", label: "Downloads", icon: Download },
] as const;

const bottom = [
  { to: "/settings", label: "Settings", icon: Settings },
  { to: "/profile", label: "Profile", icon: User },
] as const;

export function Sidebar() {
  const { collapsed, toggle, mobileOpen, setMobileOpen } = useSidebar();
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  return (
    <>
      {/* Mobile drawer backdrop */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setMobileOpen(false)}
          />
        )}
      </AnimatePresence>

      <motion.aside
        initial={false}
        animate={{ width: collapsed ? 84 : 260 }}
        transition={{ type: "spring", stiffness: 260, damping: 30 }}
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex h-full flex-col border-r border-border/60 bg-sidebar text-sidebar-foreground",
          "lg:relative lg:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
          "transition-transform duration-300",
        )}
      >
        <div className="flex items-center justify-between px-5 pt-6 pb-4">
          <Logo compact={collapsed} />
          <div className="flex items-center gap-1">
            <button onClick={toggle} className="hidden lg:grid size-8 place-items-center rounded-full hover:bg-white/5 text-muted-foreground">
              {collapsed ? <ChevronRight className="size-4" /> : <ChevronLeft className="size-4" />}
            </button>
            <button onClick={() => setMobileOpen(false)} className="lg:hidden grid size-8 place-items-center rounded-full hover:bg-white/5">
              <X className="size-4" />
            </button>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto scrollbar-hide px-3 py-2">
          <ul className="space-y-1">
            {items.map(({ to, label, icon: Icon }) => {
              const active = pathname === to || (to !== "/" && pathname.startsWith(to));
              return (
                <li key={to}>
                  <Link
                    to={to}
                    onClick={() => setMobileOpen(false)}
                    className={cn(
                      "group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                      active ? "text-foreground" : "text-muted-foreground hover:text-foreground hover:bg-white/5",
                    )}
                  >
                    {active && (
                      <motion.span
                        layoutId="sidebar-active"
                        className="absolute inset-0 rounded-xl bg-gradient-brand-soft border border-white/10"
                        transition={{ type: "spring", stiffness: 400, damping: 32 }}
                      />
                    )}
                    <Icon className={cn("relative size-5 shrink-0", active && "text-foreground")} />
                    {!collapsed && <span className="relative truncate">{label}</span>}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="mt-auto border-t border-border/60 px-3 py-3">
          <ul className="space-y-1">
            {bottom.map(({ to, label, icon: Icon }) => {
              const active = pathname === to;
              return (
                <li key={to}>
                  <Link
                    to={to}
                    onClick={() => setMobileOpen(false)}
                    className={cn(
                      "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                      active ? "text-foreground bg-white/5" : "text-muted-foreground hover:text-foreground hover:bg-white/5",
                    )}
                  >
                    <Icon className="size-5 shrink-0" />
                    {!collapsed && <span className="truncate">{label}</span>}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      </motion.aside>
    </>
  );
}
