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
  | "treeCanopyPct";

export const CROSS_CITY_DEFAULT_ENCODINGS = {
  x: "selectedTimeTemperatureC",
  y: "medianHouseholdIncomeUsd",
  size: "population",
  fill: "treeCanopyPct",
} as const satisfies Record<"x" | "y" | "size" | "fill", CrossCityMetricKey>;

export type CrossCityMetrics = {
  selectedTimeTemperatureC: number | null;
  medianHouseholdIncomeUsd: number | null;
  population: number | null;
  treeCanopyPct: number | null;
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
