import type { CrossCityAreaRecord, CrossCityMetricKey } from "./types";

export type NumericDomain = { min: number; max: number };

const POPULATION_MAX_RADIUS = 26;
const FILL_LOW = [233, 245, 237] as const;
const FILL_HIGH = [32, 94, 65] as const;

export function metricValue(
  record: CrossCityAreaRecord,
  metric: CrossCityMetricKey,
): number | null {
  return record.metrics[metric];
}

export function metricDomain(
  records: readonly CrossCityAreaRecord[],
  metric: CrossCityMetricKey,
): NumericDomain | null {
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

function interpolate(start: number, end: number, ratio: number): number {
  return Math.round(start + (end - start) * ratio);
}

export function globalFillColor(
  value: number | null,
  domain: NumericDomain | null,
): string | null {
  if (value == null || !Number.isFinite(value) || domain == null) {
    return null;
  }
  const span = domain.max - domain.min;
  const ratio = span <= 0 ? 0.5 : Math.max(0, Math.min(1, (value - domain.min) / span));
  const rgb = FILL_LOW.map((start, index) => interpolate(start, FILL_HIGH[index] ?? start, ratio));
  return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
}
