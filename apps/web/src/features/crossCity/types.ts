export const CROSS_CITY_COMPARISON_CLOCK_LOCAL = "2024-07-08 15:00" as const;

export const CROSS_CITY_CITY_ALLOWLIST = [
  {
    id: "phoenix-az",
    label: "Phoenix, AZ",
    shortLabel: "Phoenix",
    stateAbbreviation: "AZ",
    localAreaAnalysis: "published",
  },
  {
    id: "las-vegas-nv",
    label: "Las Vegas, NV",
    shortLabel: "Las Vegas",
    stateAbbreviation: "NV",
    localAreaAnalysis: "level-1-only",
  },
  {
    id: "tucson-az",
    label: "Tucson, AZ",
    shortLabel: "Tucson",
    stateAbbreviation: "AZ",
    localAreaAnalysis: "level-1-only",
  },
  {
    id: "los-angeles-ca",
    label: "Los Angeles, CA",
    shortLabel: "Los Angeles",
    stateAbbreviation: "CA",
    localAreaAnalysis: "level-1-only",
  },
] as const;

export type CrossCityId = (typeof CROSS_CITY_CITY_ALLOWLIST)[number]["id"];

export type CrossCityMetricKey =
  | "selectedTimeTemperatureC"
  | "medianHouseholdIncomeUsd"
  | "population"
  | "treeCanopyPct"
  | "olderHousingPct";

export type CrossCityFillKey = CrossCityMetricKey | "none";

export const CROSS_CITY_DEFAULT_ENCODINGS = {
  x: "treeCanopyPct",
  y: "selectedTimeTemperatureC",
  size: "population",
  fill: "treeCanopyPct",
} as const satisfies Record<"x" | "y" | "size" | "fill", CrossCityMetricKey>;

export const CROSS_CITY_AXIS_OPTIONS: readonly {
  key: CrossCityMetricKey;
  label: string;
  shortLabel: string;
}[] = [
  {
    key: "treeCanopyPct",
    label: "Tree canopy (%)",
    shortLabel: "Tree canopy",
  },
  {
    key: "selectedTimeTemperatureC",
    label: "Selected-time temperature (°C)",
    shortLabel: "Temperature",
  },
  {
    key: "medianHouseholdIncomeUsd",
    label: "Median household income (USD)",
    shortLabel: "Income",
  },
  {
    key: "olderHousingPct",
    label: "Older housing (% units before 1980)",
    shortLabel: "Older housing",
  },
  {
    key: "population",
    label: "Population",
    shortLabel: "Population",
  },
] as const;

export const CROSS_CITY_FILL_OPTIONS: readonly {
  key: CrossCityFillKey;
  label: string;
}[] = [
  { key: "treeCanopyPct", label: "Tree canopy" },
  { key: "selectedTimeTemperatureC", label: "Temperature" },
  { key: "medianHouseholdIncomeUsd", label: "Income" },
  { key: "olderHousingPct", label: "Older housing" },
  { key: "none", label: "None" },
] as const;

export type CrossCityMetrics = {
  selectedTimeTemperatureC: number | null;
  medianHouseholdIncomeUsd: number | null;
  population: number | null;
  treeCanopyPct: number | null;
  olderHousingPct: number | null;
};

export type CrossCityAreaRecord = {
  cityId: CrossCityId;
  cityLabel: string;
  areaId: string;
  areaLabel: string;
  metrics: CrossCityMetrics;
};

export type CrossCityMetricsResponse = {
  comparisonClockLocal: string;
  areas: CrossCityAreaRecord[];
};

export function cityMeta(cityId: CrossCityId) {
  return CROSS_CITY_CITY_ALLOWLIST.find((city) => city.id === cityId) ?? CROSS_CITY_CITY_ALLOWLIST[0];
}

export function metricLabel(key: CrossCityMetricKey | "none"): string {
  if (key === "none") {
    return "None";
  }
  return CROSS_CITY_AXIS_OPTIONS.find((option) => option.key === key)?.label ?? key;
}
