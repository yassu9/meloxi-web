import { createFileRoute } from "@tanstack/react-router";
import { HomePage } from "@/components/pages/home/HomePage";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Meloxi — Premium Music Streaming" },
      { name: "description", content: "Discover trending songs, curated playlists, and new releases on Meloxi." },
      { property: "og:title", content: "Meloxi — Premium Music Streaming" },
      { property: "og:description", content: "Discover trending songs, curated playlists, and new releases on Meloxi." },
    ],
  }),
  component: HomePage,
});