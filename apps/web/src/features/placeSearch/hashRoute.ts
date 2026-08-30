import type { RouteId } from "./types";

export function placeSearchRouteFromHash(hash = typeof window === "undefined" ? "" : window.location.hash): RouteId {
  const path = hash.replace(/^#/, "") || "/";
  return path.startsWith("/phoenix-demo") ? "phoenix-demo" : "national";
}
