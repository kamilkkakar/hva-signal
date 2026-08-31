import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { buildJudgeMapCatalog } from "@/features/judgeShell/mapCatalog";
import { highlightFillPaint } from "@/features/mapInteraction/highlight";
import { FORBIDDEN_FIRST_READ, SECTION_NAV } from "./copy";

const here = path.dirname(fileURLToPath(import.meta.url));

describe("judge experience contract bindings", () => {
  const judgeShell = readFileSync(
    path.join(here, "../judgeShell/JudgeShell.tsx"),
    "utf8",
  );
  const mapCatalog = readFileSync(
    path.join(here, "../judgeShell/mapCatalog.ts"),
    "utf8",
  );
  const mapChrome = readFileSync(
    path.join(here, "../mapInteraction/MapInteractionChrome.tsx"),
    "utf8",
  );

  it("uses MapLibre with real geometry — not tile grid fallback", () => {
    expect(readFileSync(path.join(here, "../mapInteraction/MapInteractionStage.tsx"), "utf8")).toContain("maplibregl");
    expect(mapCatalog).toContain("catalogFromSnapshot");
    expect(mapCatalog).not.toMatch(/fillAuthorized.*ranking/i);
    expect(judgeShell).not.toContain("OUTLINES ONLY");
    expect(judgeShell).not.toContain("FILLS WAIT FOR A BOUND LAYER");
  });

  it("renders thermal snapshot legend chrome", () => {
    expect(mapChrome).toContain("ThermalSnapshotLegend");
    expect(
      readFileSync(path.join(here, "../mapEncoding/ThermalSnapshotLegend.tsx"), "utf8"),
    ).toContain("thermal-snapshot-legend");
  });

  it("exposes five-question IA without month/season or climate trend nav", () => {
    expect(SECTION_NAV).toHaveLength(5);
    expect(SECTION_NAV.map((row) => row.title).join(" ")).not.toMatch(/month\/season/i);
    expect(SECTION_NAV.map((row) => row.title).join(" ")).not.toMatch(/climate trend/i);
    expect(SECTION_NAV.map((row) => row.title).join(" ")).not.toMatch(/intervention effect/i);
    expect(judgeShell).toContain("SectionNav");
  });

  it("paints absolute °C on selected-time snapshot", () => {
    const catalog = buildJudgeMapCatalog({
      geometry: {
        areaId: "phoenix-demo",
        zoneGeometryVersion: "v1",
        geometrySha256: "abc",
        collection: {
          type: "FeatureCollection",
          features: [
            {
              type: "Feature",
              properties: { GEOID: "04013107401" },
              geometry: { type: "Polygon", coordinates: [] },
            },
          ],
        },
      },
      areaId: "phoenix-demo",
      result: null,
      jobStatus: null,
    });
    expect(catalog?.fill_kind).toBe("thermal_absolute");
    const paint = highlightFillPaint(catalog, {
      hoverId: null,
      selectedId: null,
      layerActive: true,
      fitGeneration: 0,
    });
    expect(JSON.stringify(paint["fill-color"])).toContain("mean_temperature_c");
  });

  it("forbids method tokens on first read", () => {
    const surface = readFileSync(path.join(here, "ThermalHero.tsx"), "utf8")
      + readFileSync(path.join(here, "DecisionDirection.tsx"), "utf8")
      + readFileSync(path.join(here, "SectionNav.tsx"), "utf8");
    for (const token of FORBIDDEN_FIRST_READ) {
      if (token === "q_A" || token === "Decision 8") continue;
      expect(surface).not.toContain(token);
    }
  });
});
