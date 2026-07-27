import { createFileRoute } from "@tanstack/react-router";
import { PlaylistsCollection } from "@/components/pages/collections/CollectionPage";
export const Route = createFileRoute("/playlists")({
  head: () => ({ meta: [{ title: "Playlists — Meloxi" }, { name: "description", content: "Curated and personal playlists on Meloxi." }, { property: "og:title", content: "Playlists — Meloxi" }, { property: "og:description", content: "Curated and personal playlists on Meloxi." }] }),
  component: PlaylistsCollection,
});
