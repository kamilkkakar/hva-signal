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
        geometry: { type: "Polygon", coordinates: [] },
      })),
    },
  };
}

describe("exploreMapState", () => {
  it("keeps outlines in loading until the analysis result is ready", () => {
    const catalog = buildJudgeMapCatalog({
      geometry: geometry(["04013107401"]),
      areaId: "phoenix-demo",
      result: null,
      jobStatus: null,
      fillAuthorized: false,
    });
    expect(catalog?.collection.features).toHaveLength(1);
    expect(exploreMapState({
      submitting: true,
      jobStatus: "queued",
      catalog,
      rankingState: "INSUFFICIENT_EVIDENCE",
    })).toBe("loading");
  });

  it("marks insufficient when the completed night cannot support ranking", () => {
    expect(
      exploreMapState({
        submitting: false,
        jobStatus: "complete",
        catalog: buildJudgeMapCatalog({
          geometry: geometry(["04013107401"]),
          areaId: "phoenix-demo",
          result: null,
          jobStatus: "complete",
          fillAuthorized: false,
        }),
        rankingState: "INSUFFICIENT_EVIDENCE",
      }),
    ).toBe("insufficient");
  });
});

describe("buildJudgeMapCatalog", () => {
  it("shows geometry outlines before a job result exists", () => {
    const catalog = buildJudgeMapCatalog({
      geometry: geometry(["04013107401", "04013107500"]),
      areaId: "phoenix-demo",
      result: null,
      jobStatus: null,
      fillAuthorized: false,
    });
    expect(catalog?.kind).toBe("aoi_outline");
    expect(catalog?.fill_authorized).toBe(false);
    expect(catalog?.collection.features).toHaveLength(2);
    expect(catalog?.zones.every((zone) => zone.has_semantic_fill === false)).toBe(true);
  });

  it("joins a ready result and authorizes fill only when ranking is ready", () => {
    const catalog = buildJudgeMapCatalog({
      geometry: geometry(["04013107401"]),
      areaId: "phoenix-demo",
      jobStatus: "complete",
      fillAuthorized: true,
      result: {
        thermal_differentiation_state: "SUFFICIENT",
        versions: { zone_geometry_version: VERSION },
        zones: [
          {
            zone_id: "04013107401",
            ranked: true,
            thermal_ordering_permitted: true,
            q_A: 0.42,
          },
        ],
      },
    });
    expect(resultIsReady("complete")).toBe(true);
    expect(catalog?.kind).toBe("historical_ordering");
    expect(catalog?.fill_authorized).toBe(true);
    expect(catalog?.zones[0]?.has_semantic_fill).toBe(true);
  });
});
