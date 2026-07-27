import { useState, useEffect, useRef } from "react";
import { Search, Bell, Sun, ChevronLeft, ChevronRight, Menu } from "lucide-react";
import { useRouter, useNavigate, useRouterState, useSearch } from "@tanstack/react-router";
import { useSidebar } from "@/contexts/SidebarContext";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

export function Header() {
  const router = useRouter();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const searchParams = useSearch({ strict: false }) as { q?: string };
  const { setMobileOpen } = useSidebar();
  const inputRef = useRef<HTMLInputElement>(null);

  const [query, setQuery] = useState(searchParams?.q || "");

  useEffect(() => {
    if (typeof searchParams?.q === "string") {
      setQuery(searchParams.q);
    }
  }, [searchParams?.q]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleInputChange = (val: string) => {
    setQuery(val);
    navigate({ to: "/search", search: { q: val }, replace: true });
  };

  const handleInputFocus = () => {
    if (pathname !== "/search") {
      navigate({ to: "/search", search: { q: query } });
    }
  };

  return (
    <header className="sticky top-0 z-30 glass">
      <div className="flex items-center gap-3 px-4 lg:px-8 h-16">
        <button className="lg:hidden grid size-9 place-items-center rounded-full hover:bg-white/5" onClick={() => setMobileOpen(true)}>
          <Menu className="size-5" />
        </button>
        <div className="hidden sm:flex items-center gap-1">
          <button onClick={() => router.history.back()} className="grid size-9 place-items-center rounded-full bg-black/40 hover:bg-black/60"><ChevronLeft className="size-4" /></button>
          <button onClick={() => router.history.forward()} className="grid size-9 place-items-center rounded-full bg-black/40 hover:bg-black/60"><ChevronRight className="size-4" /></button>
        </div>
        <div className="flex-1 max-w-xl">
          <div className="flex items-center gap-2 rounded-full bg-surface-2/80 border border-border px-4 h-10 focus-within:border-primary/60 transition-colors cursor-pointer">
            <Search className="size-4 text-muted-foreground shrink-0" />
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => handleInputChange(e.target.value)}
              onFocus={handleInputFocus}
              placeholder="Search songs, artists, albums…"
              className="flex-1 bg-transparent outline-none text-sm placeholder:text-muted-foreground"
            />
            <kbd className="hidden md:inline-flex items-center gap-1 rounded border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground">⌘K</kbd>
          </div>
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          <button className="grid size-9 place-items-center rounded-full hover:bg-white/5"><Sun className="size-4" /></button>
          <button className="relative grid size-9 place-items-center rounded-full hover:bg-white/5">
            <Bell className="size-4" />
            <span className="absolute top-2 right-2 size-1.5 rounded-full bg-primary" />
          </button>
          <Avatar className="size-9 ring-1 ring-border">
            <AvatarFallback className="bg-gradient-brand text-white text-xs font-bold">MX</AvatarFallback>
          </Avatar>
        </div>
      </div>
    </header>
  );
}
