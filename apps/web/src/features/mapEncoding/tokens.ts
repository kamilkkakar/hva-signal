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
export const SIGNAL_A_LINE_WIDTH = 1.2;
export const SIGNAL_A_HALO = "#e8eadc";
export const SIGNAL_A_HALO_WIDTH = 2.55;

export const SIGNAL_A_INSUFFICIENT_LINE = "#4e5748";
export const SIGNAL_A_INSUFFICIENT_LINE_WIDTH = 1.15;

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

export const SIGNAL_B_PUBLIC = false;
export const SIGNAL_B_HOLD_FILL = "#9aa392";
export const SIGNAL_B_HOLD_LINE = "#10140e";
export const SIGNAL_B_HOLD_OPACITY = 0.38;
export const SIGNAL_B_HOLD_ENCODING = "neutral_numeric_hold" as const;

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
