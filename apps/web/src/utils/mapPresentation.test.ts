import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import type { AreaGeometryPayload } from "@/api/areaGeometry";
import type { AnalysisResultStub } from "@/api/analysisJobs";
import { bindGeometryToAnalysis } from "./geometryJoin";
import {
  CONTEXTUAL_PREPAREDNESS_PRIORITY,
  mapPresentationFromBind,
} from "./mapPresentation";

const VERSION =
  "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f";

function ids(count: number): string[] {
  return Array.from({ length: count }, (_, index) =>
    String(40_000_000_000 + index).padStart(11, "0"),
  );
}

function geometry(geoids: string[]): AreaGeometryPayload {
  return {
    areaId: "phoenix-demo",
    zoneGeometryVersion: VERSION,
    geometrySha256: "3f16870fc801da5052b03e0f09c172feb4a1e0d6736452d22ffd6f09bb4e11f0",
    collection: {
      type: "FeatureCollection",
      features: geoids.map((geoid) => ({
        type: "Feature",
        properties: { GEOID: geoid },
        geometry: { type: "Polygon", coordinates: [] },
      })),
    },
  };
}

function insufficientResult(geoids: string[]): AnalysisResultStub {
  return {
    thermal_differentiation_state: "INSUFFICIENT",
    reference_quality: "FULL_REFERENCE",
    limitations: [CONTEXTUAL_PREPAREDNESS_PRIORITY],
    versions: { zone_geometry_version: VERSION },
    hazard_spread: {
      observed_spread: 0.0439665471923536,
      differentiation_state: "INSUFFICIENT",
      zone_geometry_version: VERSION,
    },
    zones: geoids.map((zone_id) => ({
      zone_id,
      ranked: false,
      thermal_ordering_permitted: false,
      q_A: 0.2,
    })),
  };
}

function sufficientResult(geoids: string[]): AnalysisResultStub {
  return {
    thermal_differentiation_state: "SUFFICIENT",
    reference_quality: "FULL_REFERENCE",
    versions: { zone_geometry_version: VERSION },
    hazard_spread: {
      observed_spread: 0.13548387096774192,
      differentiation_state: "SUFFICIENT",
      zone_geometry_version: VERSION,
    },
    zones: geoids.map((zone_id, index) => ({
      zone_id,
      ranked: true,
      thermal_ordering_permitted: true,
      q_A: index / 25,
    })),
  };
}

describe("mapPresentationFromBind", () => {
  it("shows 25 insufficient outlines and no ranked fills", () => {
    const geoids = ids(25);
    const bound = bindGeometryToAnalysis({
      geometry: geometry(geoids),
      requestAreaId: "phoenix-demo",
      result: insufficientResult(geoids),
    });
    const presentation = mapPresentationFromBind(bound, insufficientResult(geoids));
    expect(presentation.visualState).toBe("insufficient");
    expect(presentation.outlineCount).toBe(25);
    expect(presentation.rankedFillCount).toBe(0);
    expect(presentation.thermalOrderingVisible).toBe(false);
    expect(presentation.fallback).toBe(CONTEXTUAL_PREPAREDNESS_PRIORITY);
    expect(presentation.observedSpread).toBeCloseTo(0.0439665471923536, 12);
  });

  it("shows 25 sufficient outlines and 25 ranked fills from backend zone order", () => {
    const geoids = ids(25);
    const result = sufficientResult(geoids);
    const bound = bindGeometryToAnalysis({
      geometry: geometry(geoids),
      requestAreaId: "phoenix-demo",
      result,
    });
    const presentation = mapPresentationFromBind(bound, result);
    expect(presentation.visualState).toBe("sufficient");
    expect(presentation.outlineCount).toBe(25);
    expect(presentation.rankedFillCount).toBe(25);
    expect(presentation.thermalOrderingVisible).toBe(true);
    expect(presentation.observedSpread).toBeCloseTo(0.13548387096774192, 12);
    const ranks = presentation.collection.features.map(
      (feature) => feature.properties?.backend_order,
    );
    expect(ranks).toEqual(geoids.map((_, index) => index + 1));
  });

  it("does not render ranked fills when the bind failed", () => {
    const presentation = mapPresentationFromBind(
      { ok: false, reason: "version mismatch", rankedFillCount: 0 },
      sufficientResult(ids(25)),
    );
    expect(presentation.visualState).toBe("error");
    expect(presentation.rankedFillCount).toBe(0);
    expect(presentation.thermalOrderingVisible).toBe(false);
    expect(presentation.outlineCount).toBe(0);
  });
});

describe("frontend production sources introduce no Decision 8 analytics", () => {
  it("does not add a 0.10 threshold, top3/bottom3, or q_A rank sort", () => {
    const root = dirname(fileURLToPath(import.meta.url));
    const files = [
      "mapPresentation.ts",
      "geometryJoin.ts",
      join("..", "api", "areaGeometry.ts"),
      join("..", "features", "map", "MapStage.tsx"),
    ];
    for (const relative of files) {
      const source = readFileSync(join(root, relative), "utf8");
      expect(source).not.toMatch(/\b0\.10\b/);
      expect(source).not.toMatch(/top3|bottom3/i);
      expect(source).not.toMatch(/sort\([^)]*q_A/);
      expect(source).not.toMatch(/observed_spread\s*[<>]=?/);
    }
  });
});
