import { createFileRoute } from "@tanstack/react-router";
import { ArtistPage } from "@/components/pages/artist/ArtistPage";

export const Route = createFileRoute("/artist/$id")({
  head: () => ({ meta: [{ title: "Artist — Meloxi" }, { name: "description", content: "Artist on Meloxi." }, { property: "og:title", content: "Artist — Meloxi" }, { property: "og:description", content: "Artist on Meloxi." }] }),
  component: ArtistRoute,
});

function ArtistRoute() {
  const { id } = Route.useParams();
  return <ArtistPage id={id} />;
}
