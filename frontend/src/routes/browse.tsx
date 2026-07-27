import { createFileRoute } from "@tanstack/react-router";
import { BrowsePage } from "@/components/pages/browse/BrowsePage";
export const Route = createFileRoute("/browse")({
  head: () => ({ meta: [{ title: "Browse — Meloxi" }, { name: "description", content: "Browse genres, moods, and top charts on Meloxi." }, { property: "og:title", content: "Browse — Meloxi" }, { property: "og:description", content: "Browse genres, moods, and top charts on Meloxi." }] }),
  component: BrowsePage,
});
