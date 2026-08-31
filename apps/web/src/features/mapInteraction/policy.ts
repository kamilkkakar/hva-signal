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

export const ORDER_SHOWN_TITLE = "Nighttime historical thermal pattern";
export const ORDER_WITHHELD_TITLE = "Nighttime historical thermal pattern";
export const ORDER_WITHHELD_STATUS_LOCK =
  "THERMAL SPATIAL DIFFERENTIATION IS INSUFFICIENT FOR A DEFENSIBLE ORDERING";
export const ORDER_WITHHELD_JUDGE_SENTENCE =
  "The observed differences across the analysis area are too small to support a defensible thermal ordering, so HVA-Signal does not rank the zones.";
export const PATTERN_SUPPORT =
  "Each zone is positioned relative to its own historical 03:00 temperature record.";
export const ORDER_SHOWN_OVERLAY = PATTERN_SUPPORT;
export const ORDER_WITHHELD_OVERLAY =
  "This night is not differentiated enough to draw a relative pattern. Zones stay as geography only.";
export const NIGHTTIME_HISTORICAL_MAP_NAME = "Nighttime historical thermal pattern";
export const POSITION_MEANING =
  "Position within this zone's own 03:00 historical reference.";
export const RELATIVE_ORDER_LABEL = "Relative order within this analysis";
export const HOVER_POSITION_EVIDENCE = "Own 03:00 position";
export const HOVER_GEOGRAPHY_ONLY = "Geography only";
export const QA_EXPAND_LABEL = "Historical index";

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
export const SELECT_PROMPT = "Select a zone on the map or in the zone list.";
export const MAP_TOOLS_SUMMARY = "Map tools";
export const MAP_ADVANCED_SUMMARY = "Map tools & zone details";
export const FIT_AOI_LABEL = "Fit geography";
export const RESET_AOI_LABEL = "Reset view";
export const CLEAR_LAYER_LABEL = "Clear active layer";
export const RESTORE_LAYER_LABEL = "Restore layer";
export const CLEAR_SELECTION_LABEL = "Clear selection";
export const TABLE_CAPTION =
  "Zone list and table. Same records as the map. Keyboard: activate a zone button to select.";
export const LIST_CAPTION = "Zone identifiers for this analysis window. Same records as the map.";
export const LIST_SUMMARY = "Zone identifiers (advanced)";
export const VALUE_KIND_LABEL: Record<"q_A" | "order" | "mean_c" | "none", string> = {
  q_A: "own-night historical index",
  order: "relative order within this analysis",
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

/** Four-decimal index for expandable chrome only. Never 16-decimal primary. */
export function formatQuantile4(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) {
    return MISSING_DISPLAY;
  }
  return value.toFixed(4);
}

/** Relative order inside this analysis. Never names a server rank field, q_A, or %. */
export function formatRelativeOrder(
  order: number | null | undefined,
  of: number,
): string {
  if (order == null || !Number.isFinite(order) || of < 1) {
    return MISSING_DISPLAY;
  }
  return `${order} of ${of} in this analysis`;
}

/** @deprecated Use formatRelativeOrder. Kept as a thin alias for existing imports. */
export function formatNighttimeOrder(
  order: number | null | undefined,
  of: number,
): string {
  return formatRelativeOrder(order, of);
}

export function storySourceLabel(label: ProductSourceLabel): string {
  if (label === "REPLAY") {
    return "Replay evidence";
  }
  if (label === "CACHED") {
    return "Cached evidence";
  }
  if (label === "LIVE") {
    return "Live evidence";
  }
  if (label === "PARTIAL") {
    return "Partial evidence";
  }
  return "Evidence unavailable";
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
