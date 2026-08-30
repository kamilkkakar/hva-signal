import { catalogZone } from "./catalog";
import {
  HOVER_GEOGRAPHY_ONLY,
  HOVER_POSITION_EVIDENCE,
} from "./policy";
import type { HoverCard, InteractionCatalog, InteractionState, ZoneDetail } from "./types";
import { storyFromZone } from "./zoneStory";

function hoverLine(
  catalog: InteractionCatalog,
  zone: { geoid: string; label: string; value_display: string },
): { line: string; primary_evidence: string } {
  if (catalog.kind === "aoi_outline" || !catalog.fill_authorized) {
    return {
      primary_evidence: HOVER_GEOGRAPHY_ONLY,
      line: `Zone ${zone.geoid} · ${HOVER_GEOGRAPHY_ONLY}`,
    };
  }
  if (catalog.kind === "historical_ordering") {
    return {
      primary_evidence: HOVER_POSITION_EVIDENCE,
      line: `Zone ${zone.geoid} · ${HOVER_POSITION_EVIDENCE}`,
    };
  }
  return {
    primary_evidence: zone.value_display,
    line: `${zone.geoid} · ${zone.label} · ${zone.value_display}`,
  };
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
    ...storyFromZone(zone),
  };
}

/** Hover highlights a zone. Ordering evidence is suppressed when D8 is insufficient. */
export function hoverFromState(
  state: InteractionState,
  catalog: InteractionCatalog | null,
): HoverCard | null {
  if (!state.layerActive || !catalog) {
    return null;
  }
  const zone = catalogZone(catalog, state.hoverId);
  if (!zone) {
    return null;
  }
  const card = hoverLine(catalog, zone);
  return {
    geoid: zone.geoid,
    label: zone.label,
    value_display: zone.value_display,
    line: card.line,
    primary_evidence: card.primary_evidence,
  };
}
