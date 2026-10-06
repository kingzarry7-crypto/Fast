import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "KING ZARRY AI",
    short_name: "KZ AI",
    description: "KING ZARRY AI command centre.",
    start_url: "/dashboard",
    display: "standalone",
    background_color: "#020914",
    theme_color: "#020914",
    orientation: "portrait-primary",
    scope: "/",
    icons: [
      { src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any maskable" },
    ],
  };
}
