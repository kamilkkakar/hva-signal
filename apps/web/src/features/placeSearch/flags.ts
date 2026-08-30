/** Feature flags default OFF so phoenix-demo remains the landing product. */

import { placeSearchRouteFromHash } from "./hashRoute";

export const PLACE_SEARCH_FEATURE_FLAG = "VITE_HVA_PLACE_SEARCH";
export const PLACE_SEARCH_API_FLAG = "VITE_HVA_PLACE_SEARCH_API";

function envFlag(name: string): boolean {
  const env = import.meta.env as Record<string, string | boolean | undefined>;
  const value = env[name];
  return value === true || value === "1" || value === "true";
}

/** Public national search chrome. Default OFF. */
export function isPlaceSearchEnabled(): boolean {
  return envFlag(PLACE_SEARCH_FEATURE_FLAG);
}

/** Unpublished GET /places + POST /geographies. Default OFF → typed mocks. */
export function isPlaceSearchApiEnabled(): boolean {
  return envFlag(PLACE_SEARCH_API_FLAG);
}

export function gatedPlaceSearchLanding(
  hash?: string,
): "phoenix-demo" | "place-search" {
  if (!isPlaceSearchEnabled()) {
    return "phoenix-demo";
  }
  return placeSearchRouteFromHash(hash) === "phoenix-demo"
    ? "phoenix-demo"
    : "place-search";
}
