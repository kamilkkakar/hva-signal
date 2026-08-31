import type { CrossCityAreaRecord, CrossCityId } from "./types";
import { CROSS_CITY_CITY_ALLOWLIST, cityMeta } from "./types";

export type CityTempRange = {
  cityId: CrossCityId;
  label: string;
  shortLabel: string;
  minC: number | null;
  maxC: number | null;
  count: number;
};

export type SharedTempScale = {
  minC: number;
  maxC: number;
  cities: readonly CityTempRange[];
};

/** Shared °C scale across all cities with published temperatures (no per-city normalization). */
export function computeSharedTempScale(
  areas: readonly CrossCityAreaRecord[],
  activeCityIds: readonly CrossCityId[],
): SharedTempScale | null {
  const active = new Set(activeCityIds);
  const cities: CityTempRange[] = CROSS_CITY_CITY_ALLOWLIST.filter((c) =>
    active.has(c.id),
  ).map((c) => {
    const temps = areas
      .filter((a) => a.cityId === c.id)
      .map((a) => a.metrics.selectedTimeTemperatureC)
      .filter((t): t is number => t != null && Number.isFinite(t));
    return {
      cityId: c.id,
      label: c.label,
      shortLabel: c.shortLabel,
      minC: temps.length ? Math.min(...temps) : null,
      maxC: temps.length ? Math.max(...temps) : null,
      count: temps.length,
    };
  });

  const all = cities.flatMap((c) =>
    c.minC != null && c.maxC != null ? [c.minC, c.maxC] : [],
  );
  if (all.length === 0) return null;
  return {
    minC: Math.min(...all),
    maxC: Math.max(...all),
    cities,
  };
}

export function rangePosition(value: number, minC: number, maxC: number): number {
  if (maxC <= minC) return 0.5;
  return Math.min(1, Math.max(0, (value - minC) / (maxC - minC)));
}

export function cityHue(cityId: CrossCityId): string {
  switch (cityId) {
    case "phoenix-az":
      return "#2F6FED";
    case "las-vegas-nv":
      return "#0D9488";
    case "tucson-az":
      return "#7B4DDB";
    case "los-angeles-ca":
      return "#E67E22";
    default:
      return cityMeta(cityId).shortLabel ? "#243833" : "#243833";
  }
}
