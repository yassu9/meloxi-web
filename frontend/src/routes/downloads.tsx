import { createFileRoute } from "@tanstack/react-router";
import { DownloadsPage } from "@/components/pages/collections/CollectionPage";
export const Route = createFileRoute("/downloads")({
  head: () => ({ meta: [{ title: "Downloads — Meloxi" }, { name: "description", content: "Your offline library on Meloxi." }, { property: "og:title", content: "Downloads — Meloxi" }, { property: "og:description", content: "Your offline library on Meloxi." }] }),
  component: DownloadsPage,
});
