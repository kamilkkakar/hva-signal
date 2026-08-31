import type { CrossCityId } from "./types";
import {
  ACTIVE_CROSS_CITY_CANOPY_DISPLAY_SCALE,
  canopyDisplayRatio,
} from "./canopyDisplayScale";

type IntensityDomain = { min: number; max: number };

/**
 * City = hue family. Fill metric = lightness within that family (OKLCH).
 * Reserved hues for Yuma / Palm Springs stay documented even when those
 * places are not yet ALG1-eligible for CROSS_CITY_COMPARISON_GEOGRAPHY_V1.
 */
export type CityHueFamily = {
  id: CrossCityId | "yuma-az" | "palm-springs-ca";
  label: string;
  /** OKLCH hue degrees — max accessible separation across the curated set. */
  hue: number;
  /** OKLCH chroma (shared so equal metric → comparable intensity). */
  chroma: number;
};

export const CROSS_CITY_HUE_FAMILIES: readonly CityHueFamily[] = [
  { id: "phoenix-az", label: "Phoenix blue", hue: 250, chroma: 0.12 },
  { id: "las-vegas-nv", label: "Las Vegas teal", hue: 195, chroma: 0.11 },
  { id: "tucson-az", label: "Tucson purple", hue: 305, chroma: 0.12 },
  { id: "los-angeles-ca", label: "Los Angeles orange", hue: 55, chroma: 0.13 },
  { id: "yuma-az", label: "Yuma red/coral", hue: 25, chroma: 0.14 },
  { id: "palm-springs-ca", label: "Palm Springs gold/magenta", hue: 340, chroma: 0.12 },
] as const;

const HUE_BY_CITY: Record<CrossCityId, CityHueFamily> = {
  "phoenix-az": CROSS_CITY_HUE_FAMILIES[0]!,
  "las-vegas-nv": CROSS_CITY_HUE_FAMILIES[1]!,
  "tucson-az": CROSS_CITY_HUE_FAMILIES[2]!,
  "los-angeles-ca": CROSS_CITY_HUE_FAMILIES[3]!,
};

/** Representative (mid) city color for legend swatches / outline keys. */
export const CROSS_CITY_OUTLINE_COLORS: Record<CrossCityId, string> = {
  "phoenix-az": cityOklch("phoenix-az", 0.55),
  "las-vegas-nv": cityOklch("las-vegas-nv", 0.55),
  "tucson-az": cityOklch("tucson-az", 0.55),
  "los-angeles-ca": cityOklch("los-angeles-ca", 0.55),
};

/** Lightness band inside each hue: low metric → light, high metric → deep. */
const L_LOW_METRIC = 0.88;
const L_HIGH_METRIC = 0.42;
const L_NONE = 0.78;
const L_OUTLINE = 0.32;

function cityFamily(cityId: CrossCityId): CityHueFamily {
  return HUE_BY_CITY[cityId];
}

export function cityOklch(cityId: CrossCityId, lightness: number, chromaScale = 1): string {
  const family = cityFamily(cityId);
  const L = Math.max(0.2, Math.min(0.95, lightness));
  const C = family.chroma * chromaScale;
  return `oklch(${L.toFixed(3)} ${C.toFixed(3)} ${family.hue})`;
}

export function outlineColorForCity(cityId: CrossCityId): string {
  return cityOklch(cityId, L_OUTLINE, 1.05);
}

export function noneFillColorForCity(cityId: CrossCityId): string {
  return cityOklch(cityId, L_NONE, 0.85);
}

function ratioInDomain(value: number, domain: IntensityDomain): number {
  const span = domain.max - domain.min;
  if (span <= 0) {
    return 0.5;
  }
  return Math.max(0, Math.min(1, (value - domain.min) / span));
}

/**
 * City hue + metric intensity. Never switches to a universal palette.
 * Canopy uses CROSS_CITY_CANOPY_DISPLAY_SCALE_V1; other metrics use the
 * shared domain passed in (must be global / fixed — not visible-city).
 */
export function citySpectrumFill(
  cityId: CrossCityId,
  value: number | null,
  domain: IntensityDomain | null,
  options?: { metric?: "treeCanopyPct" | "other" | "none" },
): string | null {
  if (options?.metric === "none") {
    return noneFillColorForCity(cityId);
  }
  if (value == null || !Number.isFinite(value) || domain == null) {
    return null;
  }
  const ratio =
    options?.metric === "treeCanopyPct"
      ? canopyDisplayRatio(value, ACTIVE_CROSS_CITY_CANOPY_DISPLAY_SCALE)
      : ratioInDomain(value, domain);
  const lightness = L_LOW_METRIC - ratio * (L_LOW_METRIC - L_HIGH_METRIC);
  return cityOklch(cityId, lightness);
}

/** Neutral / copper halo — independent of city hue. */
export const CROSS_CITY_SELECTION_HALO = "#1a1510";
export const CROSS_CITY_HOVER_HALO = "#b87333";

export function hueFamilyLabel(cityId: CrossCityId): string {
  return cityFamily(cityId).label;
}
