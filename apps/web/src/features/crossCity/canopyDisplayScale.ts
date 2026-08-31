/**
 * CROSS_CITY_CANOPY_DISPLAY_SCALE_V1 — fixed display envelope for cross-city
 * tree-canopy fill intensity.
 *
 * This is a product display policy, not a physical claim that canopy only
 * exists in 0–25%. NLCD TCC is 0–100% of each 30 m cell, but arid and
 * typical western-urban tract means in this product sit well below dense
 * eastern canopy. Stretching to 0–100 would collapse desert cities into a
 * near-identical pale band; stretching to the currently displayed cities
 * would silently recolor when the city set changes.
 *
 * Evidence used to set endcaps (packaged CROSS_CITY_CANOPY_CONTRACT_V1):
 * - Phoenix / Las Vegas / Tucson tract means ≈ 0.01–4.5%
 * - Los Angeles tract means ≈ 0.9–11.6%
 * - Headroom to 25% covers denser urban tracts without pretending 100% is
 *   the visual top of this comparison surface.
 *
 * Out-of-domain values end-cap (≤0 / ≥25). Never AOI- or visible-city stretch.
 */

export const CROSS_CITY_CANOPY_DISPLAY_SCALE_VERSION =
  "CROSS_CITY_CANOPY_DISPLAY_SCALE_V1" as const;

export type CanopyOverflowPolicy = "end_cap";

export type CrossCityCanopyDisplayScale = {
  version: typeof CROSS_CITY_CANOPY_DISPLAY_SCALE_VERSION;
  unit: "%";
  domainMin: number;
  domainMax: number;
  ticks: readonly number[];
  overflow: CanopyOverflowPolicy;
  currentCityStretch: false;
  visibleCityStretch: false;
  percentileStretch: false;
};

export const CROSS_CITY_CANOPY_DISPLAY_SCALE_V1: CrossCityCanopyDisplayScale = {
  version: CROSS_CITY_CANOPY_DISPLAY_SCALE_VERSION,
  unit: "%",
  domainMin: 0,
  domainMax: 25,
  ticks: [0, 5, 10, 15, 20, 25],
  overflow: "end_cap",
  currentCityStretch: false,
  visibleCityStretch: false,
  percentileStretch: false,
};

export const ACTIVE_CROSS_CITY_CANOPY_DISPLAY_SCALE = CROSS_CITY_CANOPY_DISPLAY_SCALE_V1;

export function canopyDisplayDomain(
  scale: CrossCityCanopyDisplayScale = ACTIVE_CROSS_CITY_CANOPY_DISPLAY_SCALE,
): { min: number; max: number } {
  return { min: scale.domainMin, max: scale.domainMax };
}

export function canopyDisplayRatio(
  value: number,
  scale: CrossCityCanopyDisplayScale = ACTIVE_CROSS_CITY_CANOPY_DISPLAY_SCALE,
): number {
  if (!Number.isFinite(value)) {
    return 0.5;
  }
  const span = scale.domainMax - scale.domainMin;
  if (span <= 0) {
    return 0.5;
  }
  return Math.max(0, Math.min(1, (value - scale.domainMin) / span));
}
