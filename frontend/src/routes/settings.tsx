import { createFileRoute } from "@tanstack/react-router";
import { SettingsPage } from "@/components/pages/settings/SettingsPage";
export const Route = createFileRoute("/settings")({
  head: () => ({ meta: [{ title: "Settings — Meloxi" }, { name: "description", content: "Personalize your Meloxi experience." }, { property: "og:title", content: "Settings — Meloxi" }, { property: "og:description", content: "Personalize your Meloxi experience." }] }),
  component: SettingsPage,
});
