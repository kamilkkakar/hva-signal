export const SIGNAL_B_LAYER_TITLE = "Selected-Time Thermal Snapshot" as const;

export const SIGNAL_B_NEUTRAL_FILL = "#9aa392";
export const SIGNAL_B_NEUTRAL_LINE = "#10140e";
export const SIGNAL_B_FILL_OPACITY = 0.38;
export const SIGNAL_B_LINE_WIDTH = 1.15;
export const SIGNAL_B_PAPER = "#c2c8b4";

export const MISSING_TEMPERATURE_DISPLAY = "—";

export const CURRENT_AOI_AUTOSTRETCH = false;
export const PERCENTILE_AUTOSTRETCH = false;
export const RANK_IMPLICATION = false;

export const SIGNAL_B_MEANING_COPY =
  "Zone-level absolute °C at the requested time; descriptive only.";

export const SIGNAL_B_FOOTNOTE_COPY = "not q_A / not Decision 8";

export const SIGNAL_B_METHODOLOGY_COPY =
  "Centroid-within mean. User-facing resolution is the zone. This is a selected-time snapshot, not current conditions.";

export const SIGNAL_B_STRETCH_COPY =
  "Color is not stretched to invent contrast.";

export const SIGNAL_B_UNAVAILABLE_COPY =
  "No selected-time thermal snapshot is available for this request. Absence of a snapshot is not a safety clearance.";

export const SIGNAL_B_SOURCE_ID = "hva-signal-b-zones";
export const SIGNAL_B_FILL_LAYER_ID = "hva-signal-b-neutral-fill";
export const SIGNAL_B_LINE_LAYER_ID = "hva-signal-b-outline";

export function formatSignalBTemperatureC(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) {
    return MISSING_TEMPERATURE_DISPLAY;
  }
  return `${value.toFixed(1)} °C`;
}

export function snapshotFactsText(
  minC: number | null,
  maxC: number | null,
): string | null {
  if (minC == null || maxC == null || !Number.isFinite(minC) || !Number.isFinite(maxC)) {
    return null;
  }
  return `zone means in this snapshot: ${minC.toFixed(1)}–${maxC.toFixed(1)} °C`;
}
