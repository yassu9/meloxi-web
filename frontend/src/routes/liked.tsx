import { createFileRoute } from "@tanstack/react-router";
import { LikedSongsPage } from "@/components/pages/collections/CollectionPage";
export const Route = createFileRoute("/liked")({
  head: () => ({ meta: [{ title: "Liked Songs — Meloxi" }, { name: "description", content: "Songs you've liked on Meloxi." }, { property: "og:title", content: "Liked Songs — Meloxi" }, { property: "og:description", content: "Songs you've liked on Meloxi." }] }),
  component: LikedSongsPage,
});
