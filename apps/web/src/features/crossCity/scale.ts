import type { CrossCityAreaRecord, CrossCityMetricKey } from "./types";
import { canopyDisplayDomain } from "./canopyDisplayScale";
import { citySpectrumFill } from "./colors";
import { ACTIVE_THERMAL_DISPLAY_SCALE } from "@/features/mapEncoding/thermalDisplayScale";

export type NumericDomain = { min: number; max: number };

const POPULATION_MAX_RADIUS = 26;

/** Fixed income display band for fill intensity (USD). Not visible-city stretch. */
export const CROSS_CITY_INCOME_DISPLAY_DOMAIN: NumericDomain = {
  min: 20_000,
  max: 160_000,
};

/** Older-housing share display band (% of units built before 1980). */
export const CROSS_CITY_OLDER_HOUSING_DISPLAY_DOMAIN: NumericDomain = {
  min: 0,
  max: 100,
};

export function metricValue(
  record: CrossCityAreaRecord,
  metric: CrossCityMetricKey,
): number | null {
  return record.metrics[metric];
}

/**
 * Shared quantitative domain across the full published payload.
 * Never rescale to the currently visible / isolated city set.
 */
export function metricDomain(
  records: readonly CrossCityAreaRecord[],
  metric: CrossCityMetricKey,
): NumericDomain | null {
  if (metric === "treeCanopyPct") {
    return canopyDisplayDomain();
  }
  if (metric === "selectedTimeTemperatureC") {
    return {
      min: ACTIVE_THERMAL_DISPLAY_SCALE.domainMin,
      max: ACTIVE_THERMAL_DISPLAY_SCALE.domainMax,
    };
  }
  if (metric === "medianHouseholdIncomeUsd") {
    return CROSS_CITY_INCOME_DISPLAY_DOMAIN;
  }
  if (metric === "olderHousingPct") {
    return CROSS_CITY_OLDER_HOUSING_DISPLAY_DOMAIN;
  }
  const values = records
    .map((record) => metricValue(record, metric))
    .filter((value): value is number => value != null && Number.isFinite(value));
  if (values.length === 0) {
    return null;
  }
  return {
    min: Math.min(...values),
    max: Math.max(...values),
  };
}

function clampPhysicalAxisDomain(
  metric: CrossCityMetricKey,
  domain: NumericDomain,
): NumericDomain {
  if (metric === "treeCanopyPct" || metric === "olderHousingPct") {
    return {
      min: Math.max(0, domain.min),
      max: Math.min(100, Math.max(0, domain.max)),
    };
  }
  if (metric === "population" || metric === "medianHouseholdIncomeUsd") {
    return { min: Math.max(0, domain.min), max: Math.max(0, domain.max) };
  }
  return domain;
}

/** Axis domain from an explicit record subset (e.g. focused single-city scale). */
export function axisDomainFromRecords(
  records: readonly CrossCityAreaRecord[],
  metric: CrossCityMetricKey,
  paddingRatio = 0.08,
): NumericDomain | null {
  const values = records
    .map((record) => metricValue(record, metric))
    .filter((value): value is number => value != null && Number.isFinite(value));
  if (values.length === 0) {
    return null;
  }
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) {
    const pad = Math.max(Math.abs(min) * paddingRatio, metric === "treeCanopyPct" ? 0.5 : 1);
    return clampPhysicalAxisDomain(metric, { min: min - pad, max: max + pad });
  }
  const pad = (max - min) * paddingRatio;
  return clampPhysicalAxisDomain(metric, { min: min - pad, max: max + pad });
}

export function radiusFromPopulation(
  population: number | null,
  domain: NumericDomain | null,
): number | null {
  if (population == null || !Number.isFinite(population) || population <= 0 || domain == null) {
    return null;
  }
  const max = Math.max(domain.max, 1);
  return Number(((Math.sqrt(population) / Math.sqrt(max)) * POPULATION_MAX_RADIUS).toFixed(2));
}

/** @deprecated Prefer citySpectrumFill — kept for test migration clarity. */
export function globalFillColor(
  value: number | null,
  domain: NumericDomain | null,
  cityId: CrossCityAreaRecord["cityId"] = "phoenix-az",
): string | null {
  return citySpectrumFill(cityId, value, domain, { metric: "treeCanopyPct" });
}

export function fillColorForMetric(
  cityId: CrossCityAreaRecord["cityId"],
  fillMetric: CrossCityMetricKey | "none",
  value: number | null,
  domain: NumericDomain | null,
): string | null {
  if (fillMetric === "none") {
    return citySpectrumFill(cityId, null, null, { metric: "none" });
  }
  return citySpectrumFill(cityId, value, domain, {
    metric: fillMetric === "treeCanopyPct" ? "treeCanopyPct" : "other",
  });
}
