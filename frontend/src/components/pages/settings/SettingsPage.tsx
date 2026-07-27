import { PageTransition } from "@/components/layout/PageTransition";
import { Switch } from "@/components/ui/switch";

const sections = [
  { title: "Theme", desc: "Dark theme is optimized for Meloxi's premium visual identity.", control: <Switch defaultChecked /> },
  { title: "High-fidelity audio", desc: "Lossless streaming up to 24-bit / 192 kHz.", control: <Switch defaultChecked /> },
  { title: "Crossfade", desc: "Smoothly blend the end of one track into the next.", control: <Switch /> },
  { title: "Normalize volume", desc: "Consistent loudness across your library.", control: <Switch defaultChecked /> },
  { title: "Autoplay recommendations", desc: "Keep the music going when your queue ends.", control: <Switch defaultChecked /> },
];

const accents = [
  ["#a855f7", "#22d3ee"], ["#ec4899", "#f59e0b"], ["#22c55e", "#0ea5e9"], ["#f43f5e", "#8b5cf6"], ["#facc15", "#f97316"],
];

const shortcuts = [
  ["Play / Pause", "Space"],
  ["Next track", "→"],
  ["Previous track", "←"],
  ["Volume up", "↑"],
  ["Volume down", "↓"],
  ["Toggle shuffle", "S"],
  ["Toggle repeat", "R"],
  ["Toggle lyrics", "L"],
];

export function SettingsPage() {
  return (
    <PageTransition>
      <div className="mx-auto max-w-4xl px-4 lg:px-8 py-8 space-y-10">
        <div>
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight">Settings</h1>
          <p className="mt-2 text-muted-foreground">Personalize your Meloxi experience.</p>
        </div>

        <section className="space-y-4">
          <h2 className="text-lg font-bold">Accent color</h2>
          <div className="flex flex-wrap gap-3">
            {accents.map(([a, b], i) => (
              <button key={i} className="size-12 rounded-full ring-2 ring-transparent hover:ring-white/40" style={{ background: `linear-gradient(135deg, ${a}, ${b})` }} />
            ))}
          </div>
        </section>

        <section className="glass rounded-2xl border border-white/10 divide-y divide-border/50 overflow-hidden">
          {sections.map((s) => (
            <div key={s.title} className="flex items-center justify-between gap-4 px-5 py-4">
              <div className="min-w-0">
                <div className="text-sm font-semibold">{s.title}</div>
                <div className="text-xs text-muted-foreground">{s.desc}</div>
              </div>
              <div className="shrink-0">{s.control}</div>
            </div>
          ))}
        </section>

        <section className="space-y-4">
          <h2 className="text-lg font-bold">Language</h2>
          <select className="w-full max-w-xs rounded-xl bg-surface-2 border border-border px-4 h-11 text-sm outline-none focus:border-primary/60">
            {["English", "Français", "Español", "日本語", "Deutsch", "Português"].map((l) => <option key={l}>{l}</option>)}
          </select>
        </section>

        <section className="space-y-4">
          <h2 className="text-lg font-bold">Keyboard shortcuts</h2>
          <div className="glass rounded-2xl border border-white/10 divide-y divide-border/50 overflow-hidden">
            {shortcuts.map(([k, v]) => (
              <div key={k} className="flex items-center justify-between px-5 py-3 text-sm">
                <span>{k}</span>
                <kbd className="rounded border border-border bg-surface-2 px-2 py-0.5 text-xs font-mono">{v}</kbd>
              </div>
            ))}
          </div>
        </section>

        <section className="glass rounded-2xl border border-white/10 p-6">
          <h2 className="text-lg font-bold">About Meloxi</h2>
          <p className="mt-2 text-sm text-muted-foreground">Meloxi is a premium music streaming experience designed for people who love how music sounds and feels.</p>
          <p className="mt-1 text-xs text-muted-foreground">Version 1.0.0 · Frontend preview</p>
        </section>
      </div>
    </PageTransition>
  );
}
