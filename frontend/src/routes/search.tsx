import { createFileRoute } from "@tanstack/react-router";
import { SearchPage } from "@/components/pages/search/SearchPage";
export const Route = createFileRoute("/search")({
  validateSearch: (search: Record<string, unknown>) => ({
    q: (search.q as string) || "",
  }),
  head: () => ({
    meta: [
      { title: "Search — Meloxi" },
      { name: "description", content: "Search songs, artists, albums, and playlists on Meloxi." },
      { property: "og:title", content: "Search — Meloxi" },
      { property: "og:description", content: "Search songs, artists, albums, and playlists on Meloxi." },
    ],
  }),
  component: SearchPage,
});
