import { describe, expect, it } from "vitest";
import type { AreaGeometryPayload } from "@/api/areaGeometry";
import { buildJudgeMapCatalog, exploreMapState, resultIsReady } from "./mapCatalog";

const VERSION = "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f";

function geometry(geoids: string[]): AreaGeometryPayload {
  return {
    areaId: "phoenix-demo",
    zoneGeometryVersion: VERSION,
    geometrySha256: "3f16870fc801da5052b03e0f09c172feb4a1e0d6736452d22ffd6f09bb4e11f0",
    collection: {
      type: "FeatureCollection",
      features: geoids.map((GEOID) => ({
        type: "Feature",
        properties: { GEOID },
        geometry: {
          type: "Polygon",
          coordinates: [
            [
              [-112.1, 33.4],
              [-112.09, 33.4],
              [-112.09, 33.41],
              [-112.1, 33.41],
              [-112.1, 33.4],
            ],
          ],
        },
      })),
    },
  };
}

describe("exploreMapState", () => {
  it("marks sufficient when selected-time snapshot fills are authorized", () => {
    const catalog = buildJudgeMapCatalog({
      geometry: geometry(["04013107401"]),
      areaId: "phoenix-demo",
      result: null,
      jobStatus: "complete",
    });
    expect(catalog?.kind).toBe("selected_time_snapshot");
    expect(exploreMapState({
      submitting: false,
      jobStatus: "complete",
      catalog,
      rankingState: "INSUFFICIENT_EVIDENCE",
    })).toBe("sufficient");
  });

  it("keeps loading until geometry exists", () => {
    expect(exploreMapState({
      submitting: true,
      jobStatus: "queued",
      catalog: null,
      rankingState: "INSUFFICIENT_EVIDENCE",
    })).toBe("loading");
  });
});

describe("buildJudgeMapCatalog", () => {
  it("binds cached Signal B means to real polygon geometry", () => {
    const catalog = buildJudgeMapCatalog({
      geometry: geometry(["04013107401", "04013107500"]),
      areaId: "phoenix-demo",
      result: null,
      jobStatus: null,
    });
    expect(catalog?.kind).toBe("selected_time_snapshot");
    expect(catalog?.fill_kind).toBe("thermal_absolute");
    expect(catalog?.fill_authorized).toBe(true);
    expect(catalog?.collection.features).toHaveLength(25);
    expect(catalog?.collection.features.some((feature) => feature.geometry != null)).toBe(true);
    expect(catalog?.zones.every((zone) => zone.value_kind === "mean_c")).toBe(true);
    expect(catalog?.zones.some((zone) => zone.has_semantic_fill)).toBe(true);
  });

  it("does not fall back to rectangular tile grid catalog kinds", () => {
    const catalog = buildJudgeMapCatalog({
      geometry: geometry(["04013107401"]),
      areaId: "phoenix-demo",
      jobStatus: "complete",
      result: {
        thermal_differentiation_state: "INSUFFICIENT",
        versions: { zone_geometry_version: VERSION },
        zones: [],
      },
    });
    expect(catalog?.kind).not.toBe("aoi_outline");
    expect(catalog?.kind).toBe("selected_time_snapshot");
    expect(resultIsReady("complete")).toBe(true);
  });
});
