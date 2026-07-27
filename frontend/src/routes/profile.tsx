import { createFileRoute } from "@tanstack/react-router";
import { ProfilePage } from "@/components/pages/collections/CollectionPage";
export const Route = createFileRoute("/profile")({
  head: () => ({ meta: [{ title: "Profile — Meloxi" }, { name: "description", content: "Your Meloxi profile." }, { property: "og:title", content: "Profile — Meloxi" }, { property: "og:description", content: "Your Meloxi profile." }] }),
  component: ProfilePage,
});
