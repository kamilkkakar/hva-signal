import { catalogFromSnapshot } from "@/features/mapInteraction/fromSnapshot";
import type { InteractionCatalog } from "@/features/mapInteraction";
import type { ZoneMapProperties } from "@/features/areaContext";
import type { CrossCityAreaRecord } from "@/features/crossCity/types";
import type { CityId } from "./types";

export type CityGeometry = {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    properties: Record<string, unknown>;
    geometry: unknown;
  }>;
};

export type PublishedMapContract = {
  cityId: CityId;
  geometry_count: number;
  data_count: number;
  joinable_zone_ids: number;
  bindable_temperature_values: number;
  fill_expression_finite: number;
};

const GEOID_DIGITS = /^\d+$/;

/** Census tract GEOID as an 11-digit string (leading zeros preserved). */
export function normalizeGeoid(value: unknown): string {
  const raw = String(value ?? "").trim();
  if (!raw) return "";
  if (GEOID_DIGITS.test(raw)) return raw.padStart(11, "0");
  return raw;
}

export function featureGeoid(feature: CityGeometry["features"][number]): string {
  const props = feature.properties ?? {};
  return normalizeGeoid(props.GEOID ?? props.zone_id ?? props.geoid);
}

function recordGeoid(record: CrossCityAreaRecord): string {
  return normalizeGeoid(record.areaId);
}

/**
 * Join published geometry to cross-city observation rows.
 * Fails closed: missing temps are coverage=missing (outline only), never invented.
 */
export function buildPublishedCityCatalog(
  geometry: CityGeometry,
  records: readonly CrossCityAreaRecord[],
  options?: { timezone?: string; targetTimestamp?: string },
): InteractionCatalog {
  const recordMap = new Map<string, CrossCityAreaRecord>();
  for (const record of records) {
    const id = recordGeoid(record);
    if (id) recordMap.set(id, record);
  }

  const zones = geometry.features.map((feature) => {
    const geoid = featureGeoid(feature);
    const record = recordMap.get(geoid);
    const temp = record?.metrics.selectedTimeTemperatureC ?? null;
    const finite = temp != null && Number.isFinite(temp);
    return {
      zone_id: geoid,
      mean_temperature_c: finite ? temp : null,
      coverage_status: finite ? "valid" : "missing",
    };
  });

  return catalogFromSnapshot({
    zones,
    geometry,
    targetTimestamp: options?.targetTimestamp ?? "2024-07-08T15:00:00",
    timezone: options?.timezone ?? "America/Phoenix",
    source: "fortyguard_cached",
    dataStatus: "cached",
  });
}

export function assertPublishedMapContract(
  cityId: CityId,
  geometry: CityGeometry,
  records: readonly CrossCityAreaRecord[],
  catalog: InteractionCatalog,
): PublishedMapContract {
  const geometryIds = new Set(
    geometry.features.map(featureGeoid).filter(Boolean),
  );
  const dataIds = new Set(records.map(recordGeoid).filter(Boolean));
  let joinable = 0;
  for (const id of geometryIds) {
    if (dataIds.has(id)) joinable += 1;
  }

  const bindable = catalog.zones.filter(
    (zone) =>
      zone.has_semantic_fill &&
      zone.coverage === "valid" &&
      zone.value_display !== "—",
  ).length;

  const fillFinite = catalog.collection.features.filter((feature) => {
    const value = feature.properties.mean_temperature_c;
    return typeof value === "number" && Number.isFinite(value);
  }).length;

  const report: PublishedMapContract = {
    cityId,
    geometry_count: geometry.features.length,
    data_count: records.length,
    joinable_zone_ids: joinable,
    bindable_temperature_values: bindable,
    fill_expression_finite: fillFinite,
  };

  const expected = 25;
  const ok =
    report.geometry_count === expected &&
    report.data_count === expected &&
    report.joinable_zone_ids === expected &&
    report.bindable_temperature_values === expected &&
    report.fill_expression_finite === expected;

  if (!ok && import.meta.env.DEV) {
    // Loud in development: geometry without bindable metric must never look like a product map.
    // eslint-disable-next-line no-console
    console.error(
      `[published-map-contract] ${cityId} FAILED`,
      report,
      "Geometry exists but map metric cannot bind — refusing silent empty canvas.",
    );
  }

  return report;
}

function finiteMetric(value: number | null | undefined): boolean {
  return value != null && Number.isFinite(value);
}

/**
 * Cross-city context values are already published comparison metrics. Authorize
 * an individual layer only when that metric is actually present for the zone.
 * This does not authorize a combined score or turn context into thermal rank.
 */
export function contextZonesFromRecords(
  records: readonly CrossCityAreaRecord[],
): ZoneMapProperties[] {
  return records.map((record) => ({
    zone_id: record.areaId,
    census_tract_geoid: normalizeGeoid(record.areaId),
    canopy_cover_share: record.metrics.treeCanopyPct,
    median_household_income: record.metrics.medianHouseholdIncomeUsd,
    share_pre_1980_housing: record.metrics.olderHousingPct,
    canopy_comparison_allowed: finiteMetric(record.metrics.treeCanopyPct),
    income_comparison_allowed: finiteMetric(record.metrics.medianHouseholdIncomeUsd),
    older_housing_comparison_allowed: finiteMetric(record.metrics.olderHousingPct),
    cooling_site_status: "unknown",
    combined_score_authorized: false as const,
  }));
}

type CacheEntry = {
  geometry: CityGeometry;
  geometryVersion: string;
  fetchedAt: number;
};

const geometryCache = new Map<CityId, CacheEntry>();

export function cachedCityGeometry(cityId: CityId): CityGeometry | null {
  return geometryCache.get(cityId)?.geometry ?? null;
}

export function putCityGeometryCache(
  cityId: CityId,
  geometry: CityGeometry,
  geometryVersion = "published",
): void {
  geometryCache.set(cityId, {
    geometry,
    geometryVersion,
    fetchedAt: Date.now(),
  });
}

export function clearCityGeometryCacheForTests(): void {
  geometryCache.clear();
}

export function publishedGeometryCacheKeys(): CityId[] {
  return [...geometryCache.keys()];
}
