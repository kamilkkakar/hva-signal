import {
  signalAFillPaint,
  signalALinePaint,
} from "@/features/mapEncoding";
import {
  INTERACTION_HOVER_LINE,
  INTERACTION_HOVER_LINE_WIDTH,
  INTERACTION_SELECT_LINE,
  INTERACTION_SELECT_LINE_WIDTH,
} from "./policy";
import type { InteractionCatalog, InteractionState } from "./types";

export type InteractionFillPaint = {
  "fill-color": unknown;
  "fill-opacity": unknown;
};

export type InteractionLinePaint = {
  "line-color": unknown;
  "line-width": unknown;
};

function maxAuthorizedOrder(catalog: InteractionCatalog): number {
  let max = 0;
  for (const zone of catalog.zones) {
    if (zone.relative_order_of != null) {
      max = Math.max(max, zone.relative_order_of);
    }
    if (zone.relative_order != null) {
      max = Math.max(max, zone.relative_order);
    }
  }
  return max > 0 ? max : 25;
}

/**
 * Authorized fills use RESCUE-E historical-position tokens.
 * Insufficient / unauthorized stays outline-only (opacity 0).
 */
export function highlightFillPaint(
  catalog: InteractionCatalog | null,
  state: InteractionState,
): InteractionFillPaint {
  const authorized = Boolean(state.layerActive && catalog?.fill_authorized);
  return signalAFillPaint({
    authorized,
    maxOrder: catalog ? maxAuthorizedOrder(catalog) : 25,
  });
}

export function highlightLinePaint(
  catalog: InteractionCatalog | null,
  state: InteractionState,
): InteractionLinePaint {
  const authorized = Boolean(state.layerActive && catalog?.fill_authorized);
  const base = signalALinePaint(authorized);
  return {
    "line-color": [
      "case",
      ["boolean", ["feature-state", "selected"], false],
      INTERACTION_SELECT_LINE,
      ["boolean", ["feature-state", "hover"], false],
      INTERACTION_HOVER_LINE,
      base["line-color"],
    ],
    "line-width": [
      "case",
      ["boolean", ["feature-state", "selected"], false],
      INTERACTION_SELECT_LINE_WIDTH,
      ["boolean", ["feature-state", "hover"], false],
      INTERACTION_HOVER_LINE_WIDTH,
      base["line-width"],
    ],
  };
}

export function featureStatePatch(
  state: InteractionState,
  geoid: string,
): { hover: boolean; selected: boolean } {
  return {
    hover: state.layerActive && state.hoverId === geoid,
    selected: state.layerActive && state.selectedId === geoid,
  };
}
