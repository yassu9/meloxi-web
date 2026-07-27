import { createFileRoute } from "@tanstack/react-router";
import { AlbumPage } from "@/components/pages/album/AlbumPage";

export const Route = createFileRoute("/album/$id")({
  head: () => ({ meta: [{ title: "Album — Meloxi" }, { name: "description", content: "Album on Meloxi." }, { property: "og:title", content: "Album — Meloxi" }, { property: "og:description", content: "Album on Meloxi." }] }),
  component: AlbumRoute,
});

function AlbumRoute() {
  const { id } = Route.useParams();
  return <AlbumPage id={id} />;
}
