import { createFileRoute } from "@tanstack/react-router";
import { ArtistsCollection } from "@/components/pages/collections/CollectionPage";
export const Route = createFileRoute("/artists")({
  head: () => ({ meta: [{ title: "Artists — Meloxi" }, { name: "description", content: "Discover artists on Meloxi." }, { property: "og:title", content: "Artists — Meloxi" }, { property: "og:description", content: "Discover artists on Meloxi." }] }),
  component: ArtistsCollection,
});
