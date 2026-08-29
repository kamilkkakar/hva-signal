import { describe, expect, it } from "vitest";
import type { AreaGeometryPayload } from "@/api/areaGeometry";
import type { AnalysisResultStub } from "@/api/analysisJobs";
import { bindGeometryToAnalysis, featureCollectionBounds } from "./geometryJoin";

const VERSION =
  "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f";

function ids(count: number): string[] {
  return Array.from({ length: count }, (_, index) =>
    String(40_000_000_000 + index).padStart(11, "0"),
  );
}

function collection(geoids: string[]): AreaGeometryPayload["collection"] {
  return {
    type: "FeatureCollection",
    features: geoids.map((geoid) => ({
      type: "Feature",
      properties: { GEOID: geoid },
      geometry: { type: "Polygon", coordinates: [] },
    })),
  };
}

function geometry(geoids: string[], areaId = "phoenix-demo"): AreaGeometryPayload {
  return {
    areaId,
    zoneGeometryVersion: VERSION,
    geometrySha256: "3f16870fc801da5052b03e0f09c172feb4a1e0d6736452d22ffd6f09bb4e11f0",
    collection: collection(geoids),
  };
}

function result(
  geoids: string[],
  overrides?: Partial<AnalysisResultStub>,
): AnalysisResultStub {
  return {
    thermal_differentiation_state: "INSUFFICIENT",
    versions: { zone_geometry_version: VERSION },
    zones: geoids.map((zone_id) => ({
      zone_id,
      ranked: false,
      thermal_ordering_permitted: false,
    })),
    ...overrides,
  };
}

describe("bindGeometryToAnalysis", () => {
  it("joins 25 geometry GEOIDs to 25 analysis zone_ids", () => {
    const geoids = ids(25);
    const bound = bindGeometryToAnalysis({
      geometry: geometry(geoids),
      requestAreaId: "phoenix-demo",
      result: result(geoids),
    });
    expect(bound.ok).toBe(true);
    if (bound.ok) {
      expect(bound.featureCount).toBe(25);
      expect(bound.joinedCount).toBe(25);
      expect(bound.missingAnalysisGeoids).toHaveLength(0);
      expect(bound.extraGeometryGeoids).toHaveLength(0);
      expect(bound.collection.features.every((f) => f.properties?.GEOID)).toBe(true);
    }
  });

  it("fails closed on a missing analysis GEOID", () => {
    const geoids = ids(25);
    const bound = bindGeometryToAnalysis({
      geometry: geometry(geoids),
      requestAreaId: "phoenix-demo",
      result: result(geoids.slice(1)),
    });
    expect(bound.ok).toBe(false);
    if (!bound.ok) {
      expect(bound.rankedFillCount).toBe(0);
    }
  });

  it("fails closed on an extra geometry GEOID", () => {
    const geoids = ids(25);
    const bound = bindGeometryToAnalysis({
      geometry: geometry([...geoids, "99999999999"]),
      requestAreaId: "phoenix-demo",
      result: result(geoids),
    });
    expect(bound.ok).toBe(false);
  });

  it("fails closed on duplicate geometry GEOIDs", () => {
    const geoids = ids(25);
    geoids[1] = geoids[0] ?? "00000000000";
    const bound = bindGeometryToAnalysis({
      geometry: geometry(geoids),
      requestAreaId: "phoenix-demo",
      result: result(ids(25)),
    });
    expect(bound.ok).toBe(false);
  });

  it("fails closed on zone geometry version mismatch", () => {
    const geoids = ids(25);
    const bound = bindGeometryToAnalysis({
      geometry: geometry(geoids),
      requestAreaId: "phoenix-demo",
      result: result(geoids, {
        versions: { zone_geometry_version: "OTHER.VERSION" },
      }),
    });
    expect(bound.ok).toBe(false);
    if (!bound.ok) {
      expect(bound.reason).toMatch(/version/i);
      expect(bound.rankedFillCount).toBe(0);
    }
  });

  it("derives camera bounds from feature coordinates", () => {
    const bounds = featureCollectionBounds({
      features: [
        {
          geometry: {
            type: "Polygon",
            coordinates: [
              [
                [-112.1, 33.5],
                [-112.0, 33.5],
                [-112.0, 33.6],
                [-112.1, 33.6],
                [-112.1, 33.5],
              ],
            ],
          },
        },
      ],
    });
    expect(bounds).toEqual([
      [-112.1, 33.5],
      [-112.0, 33.6],
    ]);
  });

  it("fails closed on area_id mismatch", () => {
    const geoids = ids(25);
    const bound = bindGeometryToAnalysis({
      geometry: geometry(geoids, "other-area"),
      requestAreaId: "phoenix-demo",
      result: result(geoids),
    });
    expect(bound.ok).toBe(false);
    if (!bound.ok) {
      expect(bound.reason).toMatch(/area/i);
    }
  });
});
