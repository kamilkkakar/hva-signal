/**
 * Signal A historical-position encoding tokens.
 * Domain is backend-authorized order only. Not q_A, not °C, not a stretch.
 */

export const SIGNAL_A_PAPER = "#c2c8b4";
export const SIGNAL_A_PANEL = "#d3d8c6";
export const SIGNAL_A_INK = "#10140e";
export const SIGNAL_A_MUTED = "#4e5849";

/** Winner C2b — restrained olive-ink sequential. Darker = higher historical position. */
export const SIGNAL_A_POS_STOPS = [
  "#8a9278",
  "#6c7462",
  "#4e5648",
  "#32382e",
  "#161a14",
] as const;

export const SIGNAL_A_POS_LOW = SIGNAL_A_POS_STOPS[0];
export const SIGNAL_A_POS_HIGH = SIGNAL_A_POS_STOPS[SIGNAL_A_POS_STOPS.length - 1];

/** Paper-colored unused fill. Opacity stays 0 when position is withheld. */
export const SIGNAL_A_INSUFFICIENT_FILL = SIGNAL_A_PAPER;

export const SIGNAL_A_FILL_OPACITY = 0.86;
export const SIGNAL_A_HATCH_OPACITY = 0.42;

export const SIGNAL_A_LINE = "#10140e";
export const SIGNAL_A_LINE_WIDTH = 0.75;
export const SIGNAL_A_HALO = "#e8eadc";
export const SIGNAL_A_HALO_WIDTH = 2.4;

export const SIGNAL_A_INSUFFICIENT_LINE = "#4e5748";
export const SIGNAL_A_INSUFFICIENT_LINE_WIDTH = 0.7;

export const SIGNAL_A_HATCH_LOW_ID = "hva-pos-hatch-low";
export const SIGNAL_A_HATCH_MID_ID = "hva-pos-hatch-mid";
export const SIGNAL_A_HATCH_HIGH_ID = "hva-pos-hatch-high";

export const LEGEND_LOW_LABEL = "LOWER HISTORICAL POSITION";
export const LEGEND_HIGH_LABEL = "HIGHER HISTORICAL POSITION";
export const LEGEND_AXIS = `${LEGEND_LOW_LABEL} ↔ ${LEGEND_HIGH_LABEL}`;
export const LEGEND_DENIAL =
  "Relative historical position. Not temperature. Hatch density rises with position.";
export const LEGEND_INSUFFICIENT =
  "Historical position is not shown. Outline is geography only. No ranking colors are kept.";
export const LEGEND_IDLE = "No historical position is mapped yet.";
export const LEGEND_LOADING = "Loading the analysis window.";
export const LEGEND_ERROR = "This map cannot show historical position.";
export const LEGEND_HATCH_NOTE = "Color is paired with hatch. Color alone is not enough.";

export const SIGNAL_B_PUBLIC = true;
export const SIGNAL_B_HOLD_FILL = "#9aa392";
export const SIGNAL_B_HOLD_LINE = "#10140e";
export const SIGNAL_B_HOLD_OPACITY = 0.38;
export const SIGNAL_B_HOLD_ENCODING = "neutral_numeric_hold" as const;

import {
  ACTIVE_THERMAL_DISPLAY_SCALE,
  thermalScaleAxisLabel,
  thermalScaleDomainLabel,
} from "./thermalDisplayScale";

/** @deprecated Prefer ACTIVE_THERMAL_DISPLAY_SCALE.stops — kept as alias for paint callers. */
export const THERMAL_C_STOPS = ACTIVE_THERMAL_DISPLAY_SCALE.stops;

export const THERMAL_C_LOW_LABEL = `≤${ACTIVE_THERMAL_DISPLAY_SCALE.domainMin} °C`;
export const THERMAL_C_HIGH_LABEL = `≥${ACTIVE_THERMAL_DISPLAY_SCALE.domainMax} °C`;
export const THERMAL_C_AXIS = thermalScaleAxisLabel();
export const THERMAL_C_DENIAL = `Absolute zone-mean TCM (°C) at the selected observation time. Fixed ${thermalScaleDomainLabel()} scale (${ACTIVE_THERMAL_DISPLAY_SCALE.version}) — not stretched to the current AOI.`;
export const THERMAL_C_NARROW_NOTE =
  "Area means are tightly clustered at this observation.";

/** Local-contrast endpoints on the fixed thermal palette — not a new scale. */
export const THERMAL_C_LOCAL_LOW = String(ACTIVE_THERMAL_DISPLAY_SCALE.stops[1]);
export const THERMAL_C_LOCAL_HIGH = String(
  ACTIVE_THERMAL_DISPLAY_SCALE.stops[ACTIVE_THERMAL_DISPLAY_SCALE.stops.length - 1],
);

export const THERMAL_C_LOCAL_CONTRAST_NOTE =
  "Visual enhancement only. Absolute differences remain small.";
export const THERMAL_C_LOCAL_CONTRAST_WARNING =
  "Visual enhancement only. Absolute differences remain small.";

export function thermalObservedSpanNote(minC: number, maxC: number): string {
  const spread = Math.max(0, maxC - minC);
  return `Observed range: ${minC.toFixed(1)}–${maxC.toFixed(1)} °C · Spread: approximately ${spread.toFixed(1)} °C.`;
}

/** Span below this may optionally use local contrast (OFF by default). */
export const THERMAL_C_LOCAL_CONTRAST_THRESHOLD_C = 2;

/** Context mode sequential palettes — distinct from thermal. */
export const CANOPY_STOPS = ["#e8f2e4", "#b7d6a8", "#6fa86a", "#3d7a45", "#1f4d2c"] as const;
export const INCOME_STOPS = ["#edf1f7", "#b7c6de", "#6f86b5", "#3f567f", "#243552"] as const;
export const HOUSING_STOPS = ["#f4ecdf", "#e0c49a", "#c48f4f", "#8f5a2a", "#5a3516"] as const;

export const CURRENT_AOI_AUTOSTRETCH = false;
export const PERCENTILE_AUTOSTRETCH = false;
export const RANK_FOR_B = false;

export const FORBIDDEN_LEGEND_PHRASES = [
  "safe",
  "danger",
  "risk",
  "severity",
  "intervention",
  "priority",
  "hottest",
  "coolest",
  "low risk",
  "all-clear",
] as const;
