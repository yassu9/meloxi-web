import { createFileRoute } from "@tanstack/react-router";
import { PlaylistPage } from "@/components/pages/playlist/PlaylistPage";

export const Route = createFileRoute("/playlist/$id")({
  head: () => ({ meta: [{ title: "Playlist — Meloxi" }, { name: "description", content: "Playlist on Meloxi." }, { property: "og:title", content: "Playlist — Meloxi" }, { property: "og:description", content: "Playlist on Meloxi." }] }),
  component: PlaylistRoute,
});

function PlaylistRoute() {
  const { id } = Route.useParams();
  return <PlaylistPage id={id} />;
}
