import { catalogZone } from "./catalog";
import type { InteractionCatalog, InteractionState, ZoneDetail } from "./types";

/** Detail is a projection of map state. It has no store of its own. */
export function detailFromState(
  state: InteractionState,
  catalog: InteractionCatalog | null,
): ZoneDetail | null {
  if (!state.layerActive) {
    return null;
  }
  const zone = catalogZone(catalog, state.selectedId);
  if (!zone) {
    return null;
  }
  return {
    geoid: zone.geoid,
    label: zone.label,
    value_display: zone.value_display,
    coverage: zone.coverage,
    time_label: zone.time_label,
    source_label: zone.source_label,
  };
}

export function hoverFromState(
  state: InteractionState,
  catalog: InteractionCatalog | null,
): { geoid: string; label: string; value_display: string } | null {
  if (!state.layerActive) {
    return null;
  }
  const zone = catalogZone(catalog, state.hoverId);
  if (!zone) {
    return null;
  }
  return {
    geoid: zone.geoid,
    label: zone.label,
    value_display: zone.value_display,
  };
}
