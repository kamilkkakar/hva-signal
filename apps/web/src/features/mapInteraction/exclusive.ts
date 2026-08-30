import type { InteractionCatalog } from "./types";

/** Ranked fill count. Insufficient / unauthorized catalogs contribute 0. */
export function rankedFillCount(catalog: InteractionCatalog | null): number {
  if (!catalog || !catalog.fill_authorized) {
    return 0;
  }
  return catalog.zones.filter((zone) => zone.has_semantic_fill).length;
}

/**
 * A rank map never binds a selected-time snapshot.
 * Dual A+B fill is forbidden (MAP-B L5 / Dual A+B fill NO).
 */
export function catalogForHistoricalRankMap(
  catalog: InteractionCatalog | null,
): InteractionCatalog | null {
  if (!catalog) {
    return null;
  }
  if (catalog.kind === "selected_time_snapshot") {
    return null;
  }
  return catalog;
}

export function bindExclusiveMapLayer(input: {
  lane: "A" | "B";
  historical: InteractionCatalog | null;
  snapshot: InteractionCatalog | null;
}): InteractionCatalog | null {
  if (input.lane === "A") {
    return catalogForHistoricalRankMap(input.historical);
  }
  if (input.snapshot?.kind === "historical_ordering") {
    return null;
  }
  return input.snapshot;
}
