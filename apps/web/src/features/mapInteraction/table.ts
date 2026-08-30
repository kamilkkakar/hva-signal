import type { InteractionCatalog, InteractionTableRow } from "./types";

/** First-class non-map path. Sort key is GEOID, never value. */
export function tableFromCatalog(catalog: InteractionCatalog | null): InteractionTableRow[] {
  if (!catalog) {
    return [];
  }
  return catalog.zones
    .map((zone) => ({
      geoid: zone.geoid,
      label: zone.label,
      value_display: zone.value_display,
      coverage: zone.coverage,
      time_label: zone.time_label,
      source_label: zone.source_label,
    }))
    .sort((left, right) => left.geoid.localeCompare(right.geoid));
}
