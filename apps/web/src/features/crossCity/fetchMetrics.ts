import { apiUrl } from "@/api/baseUrl";
import { crossCityDisplayName, crossCitySecondaryLabel } from "@/features/areaIdentity";
import {
  CROSS_CITY_CITY_ALLOWLIST,
  CROSS_CITY_COMPARISON_CLOCK_LOCAL,
  type CrossCityAreaRecord,
  type CrossCityId,
  type CrossCityMetricsResponse,
} from "./types";

type FlatAreaDto = {
  city_id?: string;
  city?: string;
  city_label?: string;
  area_id?: string;
  zone_id?: string;
  geoid?: string;
  area_label?: string;
  label?: string;
  selected_time_temperature_c?: unknown;
  temperature_c?: unknown;
  median_household_income?: unknown;
  median_household_income_usd?: unknown;
  population?: unknown;
  tree_canopy_pct?: unknown;
  tree_canopy_percent?: unknown;
  homes_built_before_1980?: unknown;
  older_housing_pct?: unknown;
};

type NestedCityDto = {
  city_id?: string;
  city?: string;
  city_label?: string;
  areas?: FlatAreaDto[];
};

type CrossCityMetricsDto = {
  comparison_clock_local?: unknown;
  areas?: FlatAreaDto[];
  rows?: FlatAreaDto[];
  cities?: NestedCityDto[];
};

function toNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function normalizeCityId(value: string | null | undefined): CrossCityId | null {
  const raw = (value ?? "").trim().toLowerCase().replace(/_/g, " ");
  if (!raw) {
    return null;
  }
  if (raw.includes("phoenix")) {
    return "phoenix-az";
  }
  if (raw.includes("vegas")) {
    return "las-vegas-nv";
  }
  if (raw.includes("tucson")) {
    return "tucson-az";
  }
  if (
    raw.includes("los angeles") ||
    raw.includes("los-angeles") ||
    raw.replace(/\s+/g, "") === "losangeles" ||
    raw === "la"
  ) {
    return "los-angeles-ca";
  }
  if (raw.includes("yuma")) {
    return null;
  }
  if (raw.includes("palm springs") || raw.includes("palm-springs")) {
    return null;
  }
  return null;
}

function cityLabel(cityId: CrossCityId, fallback: string | null | undefined): string {
  return (
    fallback?.trim() ??
    CROSS_CITY_CITY_ALLOWLIST.find((city) => city.id === cityId)?.label ??
    cityId
  );
}

function looksLikeGeoid(value: string): boolean {
  return /^\d{11}$/.test(value);
}

function normalizeAreaRecord(
  area: FlatAreaDto,
  inheritedCityId?: string,
  inheritedCityLabel?: string,
): CrossCityAreaRecord | null {
  const cityId = normalizeCityId(area.city_id ?? area.city ?? inheritedCityId);
  if (!cityId) {
    return null;
  }
  const areaId = String(area.area_id ?? area.zone_id ?? area.geoid ?? "").trim();
  if (!areaId) {
    return null;
  }
  const rawLabel = String(area.area_label ?? area.label ?? "").trim();
  const genericNumbered = /^(Analysis|Comparison) Area \d+$/i.test(rawLabel);
  let areaLabel: string;
  let secondaryLabel: string | undefined;
  if (looksLikeGeoid(areaId)) {
    areaLabel = crossCityDisplayName(cityId, areaId);
    secondaryLabel = crossCitySecondaryLabel(cityId, areaId) ?? undefined;
  } else if (rawLabel && !genericNumbered) {
    areaLabel = rawLabel;
  } else if (rawLabel) {
    areaLabel = rawLabel;
  } else {
    areaLabel = areaId;
  }
  if (!areaLabel) {
    return null;
  }
  return {
    cityId,
    cityLabel: cityLabel(cityId, area.city_label ?? inheritedCityLabel),
    areaId,
    areaLabel,
    secondaryLabel,
    metrics: {
      selectedTimeTemperatureC: toNumber(
        area.selected_time_temperature_c ?? area.temperature_c,
      ),
      medianHouseholdIncomeUsd: toNumber(
        area.median_household_income_usd ?? area.median_household_income,
      ),
      population: toNumber(area.population),
      treeCanopyPct: toNumber(area.tree_canopy_pct ?? area.tree_canopy_percent),
      olderHousingPct: toNumber(
        area.older_housing_pct ?? area.homes_built_before_1980,
      ),
    },
  };
}

export function normalizeCrossCityMetrics(body: unknown): CrossCityMetricsResponse {
  if (!body || typeof body !== "object") {
    throw new Error("Cross-city metrics response is not an object.");
  }
  const dto = body as CrossCityMetricsDto;
  const areas: CrossCityAreaRecord[] = [];

  for (const area of [...(dto.areas ?? []), ...(dto.rows ?? [])]) {
    const normalized = normalizeAreaRecord(area);
    if (normalized) {
      areas.push(normalized);
    }
  }

  for (const city of dto.cities ?? []) {
    for (const area of city.areas ?? []) {
      const normalized = normalizeAreaRecord(area, city.city_id ?? city.city, city.city_label);
      if (normalized) {
        areas.push(normalized);
      }
    }
  }

  return {
    comparisonClockLocal:
      typeof dto.comparison_clock_local === "string" && dto.comparison_clock_local.trim()
        ? dto.comparison_clock_local
        : CROSS_CITY_COMPARISON_CLOCK_LOCAL,
    areas,
  };
}

export async function fetchCrossCityMetrics(
  fetchImpl: typeof fetch = fetch,
): Promise<CrossCityMetricsResponse> {
  const response = await fetchImpl(apiUrl("/api/v1/cross-city/metrics"), {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Cross-city metrics could not be loaded (${response.status}).`);
  }
  return normalizeCrossCityMetrics(await response.json());
}
