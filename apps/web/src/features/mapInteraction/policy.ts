import type { MapLayerKind, ProductSourceLabel } from "./types";

export const MISSING_DISPLAY = "—";

export const INTERACTION_HOVER_LINE = "#10140e";
export const INTERACTION_SELECT_LINE = "#10140e";
export const INTERACTION_BASE_LINE = "#4e5748";
export const INTERACTION_SHARED_FILL = "#9aa392";
export const INTERACTION_PAPER = "#c2c8b4";
export const INTERACTION_FILL_OPACITY = 0.38;
export const INTERACTION_LINE_WIDTH = 1.15;
export const INTERACTION_HOVER_LINE_WIDTH = 2.05;
export const INTERACTION_SELECT_LINE_WIDTH = 2.6;

export const DECORATIVE_MAP_FORBIDDEN = true;

export const ORDER_SHOWN_TITLE = "Nighttime historical thermal order";
export const ORDER_WITHHELD_TITLE = "Order withheld — night too flat";
export const ORDER_WITHHELD_STATUS_LOCK =
  "THERMAL SPATIAL DIFFERENTIATION IS INSUFFICIENT FOR A DEFENSIBLE ORDERING";
export const ORDER_WITHHELD_JUDGE_SENTENCE =
  "The observed differences across the analysis area are too small to support a defensible thermal ordering, so HVA-Signal does not rank the zones.";
export const ORDER_SHOWN_OVERLAY =
  "Fill shows the historical 3 a.m. order. Rank is not a probability and not a heat-severity class.";
export const ORDER_WITHHELD_OVERLAY =
  "No order is shown. Rankings will not be invented from outlines.";
export const NIGHTTIME_HISTORICAL_MAP_NAME = "Nighttime historical thermal map";

export const LAYER_TITLES: Record<MapLayerKind, string> = {
  none: "No active layer",
  aoi_outline: ORDER_WITHHELD_TITLE,
  historical_ordering: ORDER_SHOWN_TITLE,
  selected_time_snapshot: "Selected-Time Thermal Snapshot",
};

export const LAYER_MEANING: Record<MapLayerKind, string> = {
  none: "There is no bindable map layer. The canvas is not shown as decoration.",
  aoi_outline: ORDER_WITHHELD_OVERLAY,
  historical_ordering: ORDER_SHOWN_OVERLAY,
  selected_time_snapshot:
    "Valid zones share one fill. Missing zones are outline only. Absolute °C is a text fact, not a color domain.",
};

export const LAYER_CLEARED_COPY = "Active layer cleared. Outlines stay. No thermal fill is shown.";
export const EMPTY_CATALOG_COPY =
  "No bindable zones. The map is withheld so it cannot be read as an empty product field.";
export const SELECT_PROMPT = "Select a zone on the map or in the zone table.";
export const FIT_AOI_LABEL = "Fit analysis window";
export const RESET_AOI_LABEL = "Reset view";
export const CLEAR_LAYER_LABEL = "Clear active layer";
export const RESTORE_LAYER_LABEL = "Restore layer";
export const CLEAR_SELECTION_LABEL = "Clear selection";
export const TABLE_CAPTION =
  "Zone table. Same records as the map. Keyboard: activate a GEOID button to select.";
export const VALUE_KIND_LABEL: Record<"q_A" | "order" | "mean_c" | "none", string> = {
  q_A: "historical quantile position",
  order: "nighttime order",
  mean_c: "zone mean °C",
  none: "no mapped value",
};

export function productSourceLabel(raw: string | null | undefined): ProductSourceLabel {
  const token = (raw ?? "").toLowerCase();
  if (token === "partial") {
    return "PARTIAL";
  }
  if (token === "replay") {
    return "REPLAY";
  }
  if (token === "cached" || token === "fortyguard_cached") {
    return "CACHED";
  }
  if (token === "live" || token === "fortyguard_live") {
    return "LIVE";
  }
  return "UNAVAILABLE";
}

export function formatMeanC(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) {
    return MISSING_DISPLAY;
  }
  return `${value.toFixed(1)} °C`;
}

export function formatQuantile(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) {
    return MISSING_DISPLAY;
  }
  return value.toFixed(3);
}

/** Chrome order line. Never says backend order, q_A, or %. */
export function formatNighttimeOrder(
  order: number | null | undefined,
  of: number,
): string {
  if (order == null || !Number.isFinite(order) || of < 1) {
    return MISSING_DISPLAY;
  }
  return `Nighttime order ${order} of ${of}`;
}

export function formatTimeLabel(
  stamp: string | null | undefined,
  timezone: string | null | undefined,
): string {
  if (!stamp) {
    return MISSING_DISPLAY;
  }
  return timezone ? `${stamp} · ${timezone}` : stamp;
}

export function zoneLabel(geoid: string, displayName?: string | null): string {
  const name = displayName?.trim();
  return name ? name : `Zone ${geoid}`;
}
