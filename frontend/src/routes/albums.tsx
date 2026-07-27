import { createFileRoute } from "@tanstack/react-router";
import { AlbumsCollection } from "@/components/pages/collections/CollectionPage";
export const Route = createFileRoute("/albums")({
  head: () => ({ meta: [{ title: "Albums — Meloxi" }, { name: "description", content: "Explore albums on Meloxi." }, { property: "og:title", content: "Albums — Meloxi" }, { property: "og:description", content: "Explore albums on Meloxi." }] }),
  component: AlbumsCollection,
});
