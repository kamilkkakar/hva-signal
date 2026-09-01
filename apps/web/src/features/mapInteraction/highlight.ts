import {
  contextQuantityFillPaint,
  signalAFillPaint,
  signalAHatchPaint,
  signalALinePaint,
  signalBThermalFillPaint,
  type ContextPaletteId,
  type SignalAHatchPaint,
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

export function contextRange(catalog: InteractionCatalog): { min: number; max: number } {
  const values = catalog.collection.features
    .map((feature) => feature.properties.context_fill_value)
    .filter((value): value is number => typeof value === "number" && Number.isFinite(value));
  if (values.length === 0) {
    return { min: 0, max: 1 };
  }
  return { min: Math.min(...values), max: Math.max(...values) };
}

function paletteFromCatalog(catalog: InteractionCatalog): ContextPaletteId {
  const title = `${catalog.layer_title} ${catalog.meaning}`.toLowerCase();
  if (title.includes("canopy") || title.includes("tree")) return "canopy";
  if (title.includes("income")) return "income";
  if (title.includes("housing") || title.includes("1980") || title.includes("homes")) {
    return "housing";
  }
  return "default";
}

/**
 * Historical ordering is shown only when the backend authorizes it.
 * Selected-time thermal conditions always use the shared absolute °C scale.
 * Context layers are relative within the displayed comparison geography and
 * are labelled as such in the legend.
 */
export function highlightFillPaint(
  catalog: InteractionCatalog | null,
  state: InteractionState,
  _options?: { enhanceLocalContrast?: boolean },
): InteractionFillPaint {
  if (catalog?.fill_kind === "context_quantity" && state.layerActive) {
    const { min, max } = contextRange(catalog);
    return contextQuantityFillPaint(min, max, paletteFromCatalog(catalog));
  }
  if (
    catalog?.fill_kind === "thermal_absolute" &&
    catalog.kind === "selected_time_snapshot" &&
    state.layerActive
  ) {
    return signalBThermalFillPaint();
  }
  const authorized = Boolean(
    state.layerActive && catalog?.fill_authorized && catalog.fill_kind === "thermal_order",
  );
  return signalAFillPaint({
    authorized,
    maxOrder: catalog ? maxAuthorizedOrder(catalog) : 25,
  });
}

/** JudgeMap hatch. Same C2b density steps as MapStage — this host is the mounted map. */
export function highlightHatchPaint(
  catalog: InteractionCatalog | null,
  state: InteractionState,
): SignalAHatchPaint {
  if (catalog?.fill_kind === "context_quantity" || catalog?.fill_kind === "thermal_absolute") {
    return signalAHatchPaint({ authorized: false, maxOrder: 25 });
  }
  const authorized = Boolean(state.layerActive && catalog?.fill_authorized);
  return signalAHatchPaint({
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
