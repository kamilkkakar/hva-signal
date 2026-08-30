import { catalogZone } from "./catalog";
import type { HoverCard, InteractionCatalog, InteractionState, ZoneDetail } from "./types";

function hoverLine(
  catalog: InteractionCatalog,
  zone: { geoid: string; label: string; value_display: string },
): string {
  if (catalog.kind === "historical_ordering") {
    return `Zone ${zone.geoid} · ${zone.value_display}`;
  }
  return `${zone.geoid} · ${zone.label} · ${zone.value_display}`;
}

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

/** MAP-B: hover is off when the nighttime order is withheld. */
export function hoverFromState(
  state: InteractionState,
  catalog: InteractionCatalog | null,
): HoverCard | null {
  if (!state.layerActive || !catalog?.fill_authorized) {
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
    line: hoverLine(catalog, zone),
  };
}
