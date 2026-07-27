import { createFileRoute } from "@tanstack/react-router";
import { LibraryPage } from "@/components/pages/library/LibraryPage";
export const Route = createFileRoute("/library")({
  head: () => ({ meta: [{ title: "Your Library — Meloxi" }, { name: "description", content: "Your playlists, albums, artists, and liked songs on Meloxi." }, { property: "og:title", content: "Your Library — Meloxi" }, { property: "og:description", content: "Your playlists, albums, artists, and liked songs on Meloxi." }] }),
  component: LibraryPage,
});
