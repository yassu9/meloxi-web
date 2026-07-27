import { createFileRoute } from "@tanstack/react-router";
import { HistoryPage } from "@/components/pages/collections/CollectionPage";
export const Route = createFileRoute("/history")({
  head: () => ({ meta: [{ title: "History — Meloxi" }, { name: "description", content: "Songs you recently played on Meloxi." }, { property: "og:title", content: "History — Meloxi" }, { property: "og:description", content: "Songs you recently played on Meloxi." }] }),
  component: HistoryPage,
});
