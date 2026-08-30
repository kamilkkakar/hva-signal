/** Chart chrome. q_A stays in selected-zone details. No probability. No qualitative bands. */

export const STRIP_KICKER = "Historical positions";
export const STRIP_MEANING =
  "Each mark is one zone on its own 3 a.m. history. Sitting together or apart is the night. These marks are not a chance of harm.";

export const AXIS_LOW = "LOWER POSITION IN OWN HISTORY";
export const AXIS_HIGH = "HIGHER POSITION IN OWN HISTORY";

export const STAMP_ORDERING_SUPPORTED = "ORDERING SUPPORTED";
export const STAMP_ORDERING_WITHHELD = "ORDERING WITHHELD";

export const SELECTED_POSITION_KICKER = "This zone’s historical position";
export const SELECTED_POSITION_EMPTY = "Click a zone. No zone selected.";
export const SELECTED_POSITION_UNAVAILABLE =
  "Historical position is not available for this zone.";
export const SELECTED_DETAILS_SUMMARY = "Exact historical position";
export const FRAME_SAME_HOUR = "same hour";

export const FORBIDDEN_CHART_CHROME = [
  "q_A",
  "Decision 8",
  "D8",
  "S =",
  "0.10",
  "quantile",
  "ECDF",
  "probability",
  "percent chance",
  "low risk",
  "high risk",
  "FortyGuard",
  "low unusualness",
  "high unusualness",
  "moderate unusualness",
] as const;

export function publishedChartChrome(): string[] {
  return [
    STRIP_KICKER,
    STRIP_MEANING,
    AXIS_LOW,
    AXIS_HIGH,
    STAMP_ORDERING_SUPPORTED,
    STAMP_ORDERING_WITHHELD,
    SELECTED_POSITION_KICKER,
    SELECTED_POSITION_EMPTY,
    SELECTED_POSITION_UNAVAILABLE,
    FRAME_SAME_HOUR,
  ];
}

export function publishedChartDetails(): string[] {
  return [SELECTED_DETAILS_SUMMARY];
}
