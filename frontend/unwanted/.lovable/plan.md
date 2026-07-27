
# Meloxi — Premium Music Streaming Frontend (UI only)

A note on the stack: this project is scaffolded on **TanStack Start + Vite + TypeScript + Tailwind v4**, not plain React + React Router. TanStack Router is fixed and cannot be swapped for `react-router-dom` in this environment. All other requested tech (React, TS, Vite, Tailwind, Framer Motion, Lucide) is used as-is. Routing will use TanStack Router file-based routes, which behave the same for the user (URL-driven pages, transitions, deep links).

Everything is **frontend only** — no backend, no auth, no real playback. Buttons, sliders, and progress bars are visually functional (local UI state) but do not stream audio.

## Design language

- Background `#070707`, cards `#171717`, purple → cyan accent gradient.
- Inter font, large headings, generous spacing, glassmorphism, soft shadows, rounded corners.
- Framer Motion for page transitions, card hover, wave/rotation micro-interactions.
- Fully responsive: mobile (bottom-nav drawer), tablet, laptop, desktop, ultrawide.

Design tokens are defined in `src/styles.css` under `@theme` + `:root` (oklch), so all colors are semantic — no hardcoded hex in components.

## Folder architecture

```text
src/
  routes/                       # TanStack Start file routes (thin — delegate to pages)
    __root.tsx                  # HTML shell, fonts, providers, AppLayout
    index.tsx                   # Home
    search.tsx
    browse.tsx
    library.tsx
    playlists.tsx
    albums.tsx
    artists.tsx
    liked.tsx
    history.tsx
    downloads.tsx
    settings.tsx
    profile.tsx
    playlist.$id.tsx
    album.$id.tsx
    artist.$id.tsx
  app/
    AppLayout.tsx               # Sidebar + Header + Outlet + RightPanel + Player
    providers.tsx               # PlayerProvider, ThemeProvider, QueueProvider
  components/
    layout/
      Sidebar.tsx, SidebarItem.tsx, SidebarCollapseToggle.tsx
      Header.tsx, SearchInput.tsx, NotificationsMenu.tsx, ProfileMenu.tsx, ThemeSwitch.tsx
      RightPanel.tsx, MobileNav.tsx, PageTransition.tsx
    pages/
      home/    (HeroBanner, FeaturedRow, RecentlyPlayed, Trending, Recommended,
                TopAlbums, TopArtists, Genres, Moods, Charts, NewReleases, ContinueListening)
      search/  (SearchHero, TrendingSearches, RecentSearches, ResultsTabs, ResultCardGrid)
      library/ (LibraryTabs, LibraryFilters, LibraryGrid)
      playlist/(PlaylistHeader, PlaylistActions, TrackList, TrackRow)
      album/   (AlbumHeader, AlbumTrackList)
      artist/  (ArtistBanner, ArtistHeader, PopularSongs, ArtistAlbums, Singles, RelatedArtists)
      settings/(SettingsSection, ThemePicker, AccentPicker, LanguageSelect,
                AudioPreferences, KeyboardShortcuts, AboutMeloxi)
    player/
      Player.tsx, Artwork.tsx, TrackMeta.tsx, TransportControls.tsx,
      ProgressBar.tsx, VolumeControl.tsx, ExtraControls.tsx, DeviceMenu.tsx,
      PlaybackSpeedMenu.tsx, MusicWave.tsx
    queue/
      QueuePanel.tsx, QueueList.tsx, QueueItem.tsx, NowPlayingCard.tsx
    lyrics/
      LyricsPanel.tsx, LyricsLine.tsx, LyricsBackdrop.tsx
    cards/
      MusicCard.tsx, AlbumCard.tsx, ArtistCard.tsx, PlaylistCard.tsx,
      GenreCard.tsx, MoodCard.tsx, CardGrid.tsx, CardRow.tsx
    ui/                        # primitives (shadcn-style + custom)
      Button, IconButton, Dropdown, Modal, Tooltip, Toast, Slider,
      ProgressBar, Skeleton, Tabs, Badge, Avatar, ScrollArea, Separator
  contexts/
    PlayerContext.tsx, QueueContext.tsx, ThemeContext.tsx, SidebarContext.tsx
  hooks/
    usePlayer.ts, useQueue.ts, useTheme.ts, useSidebar.ts,
    useMediaQuery.ts, useKeyboardShortcuts.ts, useFormattedTime.ts
  data/                         # static seed content (curated, not "dummy everywhere")
    tracks.ts, albums.ts, artists.ts, playlists.ts, genres.ts, moods.ts, lyrics.ts
  types/
    music.ts, player.ts, ui.ts
  utils/
    format.ts, cn.ts, motion.ts, gradients.ts
  styles/
    tokens.css                  # imported by styles.css (accent gradients, shadows)
    animations.css
  assets/
    icons/ (svg exports), animations/ (lottie/json if needed)
```

Rules enforced: one component per file, all shared UI in `components/ui`, no logic in route files (they just render the corresponding page component).

## Routing map (TanStack file routes)

| URL | File | Purpose |
|---|---|---|
| `/` | `routes/index.tsx` | Home |
| `/search` | `routes/search.tsx` | Search |
| `/browse` | `routes/browse.tsx` | Browse genres/moods |
| `/library` | `routes/library.tsx` | Library tabs |
| `/playlists`, `/albums`, `/artists` | siblings | Collections |
| `/liked`, `/history`, `/downloads` | siblings | Library subviews |
| `/playlist/$id`, `/album/$id`, `/artist/$id` | dynamic | Detail pages |
| `/settings`, `/profile` | siblings | Account/prefs |

`__root.tsx` supplies HTML shell + Inter font (`<link>` in `head()`) + providers. `AppLayout` renders Sidebar + Header + `<Outlet />` + optional RightPanel + fixed bottom `Player`. Each leaf route sets its own `head()` (title, description, og).

## State model (UI-only, no network)

- `PlayerContext`: `currentTrack`, `isPlaying`, `progress`, `volume`, `muted`, `shuffle`, `repeat`, `speed`, `showQueue`, `showLyrics`, `fullscreen` + setters. Progress advances via `requestAnimationFrame` while `isPlaying`, but no audio element.
- `QueueContext`: queue list, upNext, history, add/remove/reorder.
- `ThemeContext`: theme (dark default), accent color choice.
- `SidebarContext`: collapsed state persisted to `localStorage`.

## Player / Queue / Lyrics

- **Bottom Player** fixed, glass panel, all buttons requested (prev/play/next/shuffle/repeat/queue/lyrics/volume/mute/fullscreen/device/like/share/download/speed) as real UI toggles wired to `PlayerContext`.
- **QueuePanel** slides in from right; reorderable list (drag handle visual only).
- **LyricsPanel** fullscreen overlay with blurred artwork backdrop, line-by-line highlight driven by simulated `progress`.

## Data

Curated seed data in `src/data/` — real-looking tracks, albums, artists (fictional, not dummy Lorem). Used to render populated UI. No fetch, no API.

## Animations

Framer Motion `AnimatePresence` for page transitions in `AppLayout`, hover/scale on cards, spring on player expand, rotating artwork when playing, animated wave bars in `MusicWave`, skeletons during simulated load.

## Responsive strategy

- ≥1280px: sidebar + right panel visible.
- 1024–1280px: right panel collapses to icon toggle.
- 768–1024px: sidebar collapses to icon rail.
- <768px: sidebar becomes drawer, bottom nav appears, player becomes compact sheet expandable to fullscreen.

## Build sequence

1. Tokens + `styles.css` (accent gradient, shadows, radii) + Inter font in `__root.tsx` head.
2. `types/`, `data/`, `utils/`, contexts + providers.
3. `ui/` primitives.
4. `layout/` (Sidebar, Header, RightPanel, MobileNav, PageTransition) + `AppLayout`.
5. `cards/` reusable card set.
6. Player + Queue + Lyrics panels.
7. Pages (home → search → library → playlist/album/artist detail → settings → profile → browse/liked/history/downloads).
8. Route files wired to page components with per-route `head()` metadata.
9. Responsive polish + motion pass.

## Out of scope (per your instructions)

No backend, no API, no DB, no auth, no real audio playback, no simulated streaming network calls.

---

Confirm and I'll build it end-to-end, committing real files into the project.
