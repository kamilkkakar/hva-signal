import { describe, expect, it, beforeEach } from "vitest";
import {
  assertPublishedMapContract,
  buildPublishedCityCatalog,
  clearCityGeometryCacheForTests,
  featureGeoid,
  normalizeGeoid,
  putCityGeometryCache,
  cachedCityGeometry,
  type CityGeometry,
} from "./publishedCityMap";
import type { CrossCityAreaRecord } from "@/features/crossCity/types";
import type { CityId } from "./types";

function feature(geoid: string, tempHint?: number): CityGeometry["features"][number] {
  return {
    type: "Feature",
    properties: { GEOID: geoid },
    geometry: {
      type: "Polygon",
      coordinates: [
        [
          [0, 0],
          [0.01, 0],
          [0.01, 0.01],
          [0, 0],
        ],
      ],
    },
  };
}

function recordsFor(
  cityId: CityId,
  geoids: string[],
  baseTemp: number,
): CrossCityAreaRecord[] {
  return geoids.map((geoid, index) => ({
    cityId,
    cityLabel: cityId,
    areaId: geoid,
    areaLabel: `Tract ${geoid}`,
    metrics: {
      selectedTimeTemperatureC: baseTemp + index * 0.1,
      medianHouseholdIncomeUsd: 50_000,
      population: 1000,
      treeCanopyPct: 12,
      olderHousingPct: 40,
    },
  }));
}

const CITIES: Array<{ id: CityId; prefix: string; base: number }> = [
  { id: "phoenix-az", prefix: "04013103", base: 40 },
  { id: "las-vegas-nv", prefix: "32003003", base: 41 },
  { id: "tucson-az", prefix: "04019003", base: 41 },
  { id: "los-angeles-ca", prefix: "06037267", base: 23 },
];

describe("publishedCityMap contract", () => {
  beforeEach(() => {
    clearCityGeometryCacheForTests();
  });

  it("normalizes GEOID leading zeros for LA/Tucson-style ids", () => {
    expect(normalizeGeoid("6037267800")).toBe("06037267800");
    expect(normalizeGeoid(4019003302)).toBe("04019003302");
    expect(normalizeGeoid("04019003302")).toBe("04019003302");
  });

  it.each(CITIES)(
    "$id binds 25/25 geometry+temps into fill expression",
    ({ id, prefix, base }) => {
      const unique = Array.from({ length: 25 }, (_, i) => {
        const body = `${prefix}${String(i).padStart(3, "0")}`;
        return body.padStart(11, "0").slice(-11);
      });
      expect(new Set(unique).size).toBe(25);
      const geometry: CityGeometry = {
        type: "FeatureCollection",
        features: unique.map((g) => feature(g)),
      };
      const records = recordsFor(id, unique, base);
      const catalog = buildPublishedCityCatalog(geometry, records);
      const report = assertPublishedMapContract(id, geometry, records, catalog);

      expect(report.geometry_count).toBe(25);
      expect(report.data_count).toBe(25);
      expect(report.joinable_zone_ids).toBe(25);
      expect(report.bindable_temperature_values).toBe(25);
      expect(report.fill_expression_finite).toBe(25);
      expect(catalog.fill_authorized).toBe(true);
      expect(catalog.fill_kind).toBe("thermal_absolute");
      expect(catalog.collection.features.every((f) => f.geometry != null)).toBe(true);
    },
  );

  it("joins when geometry GEOID lost a leading zero but metrics kept it", () => {
    const geometry: CityGeometry = {
      type: "FeatureCollection",
      features: [feature("6037267800")],
    };
    // Force raw property without pad in feature — simulate numeric stringify
    geometry.features[0]!.properties.GEOID = "6037267800";
    const records = recordsFor("los-angeles-ca", ["06037267800"], 23);
    const catalog = buildPublishedCityCatalog(geometry, records);
    expect(featureGeoid(geometry.features[0]!)).toBe("06037267800");
    expect(catalog.zones[0]?.has_semantic_fill).toBe(true);
    expect(catalog.collection.features[0]?.properties.mean_temperature_c).toBe(23);
  });

  it("caches published geometry by city_id without refetch", () => {
    const geometry: CityGeometry = {
      type: "FeatureCollection",
      features: [feature("04019003302")],
    };
    putCityGeometryCache("tucson-az", geometry, "v1");
    expect(cachedCityGeometry("tucson-az")).toBe(geometry);
    expect(cachedCityGeometry("los-angeles-ca")).toBeNull();
  });
});
