/**
 * THERMAL_DISPLAY_SCALE_V1 — stable cross-city absolute °C display policy.
 *
 * Independent of the current request's AOI min/max.
 * Does not encode Phoenix, America/Phoenix, or analysis-area count.
 *
 * Domain validation (repo evidence, no live vendor calls):
 * - Cached Phoenix 03:00 selected-time means ≈ 33.5–33.7 °C
 * - Prompt-14 / Phoenix afternoon snapshot means ≈ 42.4 °C peak
 * - Adapter semantics: zone-mean type-1 TCM in °C (absolute, not rank)
 * - Prior 25–45 was summer-fit only — too narrow for cooler nights /
 *   cooler cities and leaves little headroom above hot desert afternoons
 *
 * Chosen envelope 15–60 °C:
 * - Lower: cooler supported cities / cooler nights can land in mid-teens
 * - Upper: hotter desert afternoons need headroom above ~45 toward 55–60
 * - Out-of-domain: end-cap colors (≤15 / ≥60), never silent AOI stretch
 */

export const THERMAL_DISPLAY_SCALE_VERSION = "THERMAL_DISPLAY_SCALE_V1" as const;

export type ThermalOverflowPolicy = "end_cap";

export type ThermalDisplayScale = {
  version: typeof THERMAL_DISPLAY_SCALE_VERSION;
  unit: "°C";
  domainMin: number;
  domainMax: number;
  /** Inclusive tick breaks for the legend axis (left → right). */
  ticks: readonly number[];
  /**
   * MapLibre-style interpolate stops: value, color, value, color, …
   * Spans the full display domain.
   */
  stops: readonly (number | string)[];
  overflow: ThermalOverflowPolicy;
  localContrastDefault: false;
  currentAoiStretch: false;
  percentileStretch: false;
};

export const THERMAL_DISPLAY_SCALE_V1: ThermalDisplayScale = {
  version: THERMAL_DISPLAY_SCALE_VERSION,
  unit: "°C",
  domainMin: 15,
  domainMax: 60,
  ticks: [15, 25, 35, 45, 55, 60],
  stops: [
    15, "#f7f0dc",
    25, "#f3e6c8",
    35, "#e4b27a",
    45, "#d07840",
    55, "#b84f2a",
    60, "#6f2414",
  ],
  overflow: "end_cap",
  localContrastDefault: false,
  currentAoiStretch: false,
  percentileStretch: false,
};

/** Active production scale — swap only via versioned policy, not ad-hoc component constants. */
export const ACTIVE_THERMAL_DISPLAY_SCALE: ThermalDisplayScale = THERMAL_DISPLAY_SCALE_V1;

export function thermalScaleStops(
  scale: ThermalDisplayScale = ACTIVE_THERMAL_DISPLAY_SCALE,
): readonly (number | string)[] {
  return scale.stops;
}

export function thermalScaleTickLabels(
  scale: ThermalDisplayScale = ACTIVE_THERMAL_DISPLAY_SCALE,
): readonly string[] {
  return scale.ticks.map((tick, index) => {
    if (index === 0) return `≤${tick}`;
    if (index === scale.ticks.length - 1) return `≥${tick}`;
    return String(tick);
  });
}

export function thermalScaleAxisLabel(
  scale: ThermalDisplayScale = ACTIVE_THERMAL_DISPLAY_SCALE,
): string {
  return `Zone-mean TCM · ${scale.unit}`;
}

export function thermalScaleDomainLabel(
  scale: ThermalDisplayScale = ACTIVE_THERMAL_DISPLAY_SCALE,
): string {
  return `${scale.domainMin}–${scale.domainMax} ${scale.unit}`;
}

export function thermalObservedBandPosition(
  observedMinC: number,
  observedMaxC: number,
  scale: ThermalDisplayScale = ACTIVE_THERMAL_DISPLAY_SCALE,
): { leftPct: number; widthPct: number } | null {
  const span = scale.domainMax - scale.domainMin;
  if (!(span > 0) || !(observedMaxC >= observedMinC)) {
    return null;
  }
  const clamp = (value: number) =>
    Math.min(scale.domainMax, Math.max(scale.domainMin, value));
  const lo = clamp(observedMinC);
  const hi = clamp(observedMaxC);
  const leftPct = ((lo - scale.domainMin) / span) * 100;
  const widthPct = Math.max(((hi - lo) / span) * 100, 4);
  return { leftPct, widthPct };
}

export function isOutsideThermalDomain(
  valueC: number,
  scale: ThermalDisplayScale = ACTIVE_THERMAL_DISPLAY_SCALE,
): boolean {
  return valueC < scale.domainMin || valueC > scale.domainMax;
}
