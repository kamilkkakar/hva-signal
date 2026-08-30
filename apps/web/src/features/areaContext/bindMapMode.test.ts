import { describe, expect, it } from "vitest";
import { catalogFromHistorical } from "@/features/mapInteraction";
import { highlightFillPaint } from "@/features/mapInteraction/highlight";
import { rankedFillCount } from "@/features/mapInteraction/exclusive";
import { CONTEXT_FILL_PROPERTY, bindMapModeCatalog, catalogUsesThermalRank, contextFillCount } from "./bindMapMode";
import { contextFillValue } from "./mapModes";
import type { ZoneMapProperties } from "./types";

const GEOID = "04013107401";
const OTHER = "04013108400";

const zones: ZoneMapProperties[] = [
  {
    zone_id: GEOID,
    census_tract_geoid: GEOID,
    canopy_cover_share: 0.12,
    median_household_income: 41000,
    share_pre_1980_housing: 0.33,
    canopy_comparison_allowed: true,
    income_comparison_allowed: false,
    older_housing_comparison_allowed: true,
    cooling_site_status: "IDENTIFIED",
    combined_score_authorized: false,
  },
  {
    zone_id: OTHER,
    census_tract_geoid: OTHER,
    canopy_cover_share: 0.2,
    median_household_income: 55000,
    share_pre_1980_housing: 0.4,
    canopy_comparison_allowed: true,
    income_comparison_allowed: true,
    older_housing_comparison_allowed: true,
    cooling_site_status: "UNKNOWN",
    combined_score_authorized: false,
  },
];

function historical(fillAuthorized: boolean) {
  return catalogFromHistorical({
    fillAuthorized,
    features: [
      {
        properties: {
          GEOID,
          zone_id: GEOID,
          backend_order: 3,
          q_A: 0.8,
          thermal_ordering_permitted: fillAuthorized,
        },
        geometry: { type: "Polygon", coordinates: [] },
      },
      {
        properties: {
          GEOID: OTHER,
          zone_id: OTHER,
          backend_order: 7,
          q_A: 0.2,
          thermal_ordering_permitted: fillAuthorized,
        },
        geometry: { type: "Polygon", coordinates: [] },
      },
    ],
  });
}

describe("MapBand context fill path", () => {
  it("wires contextFillValue onto catalog features for TREE_CANOPY", () => {
    const catalog = bindMapModeCatalog({
      historical: historical(true),
      mode: "TREE_CANOPY",
      zones,
    });
    expect(contextFillValue("TREE_CANOPY", zones[0]!)).toBe(0.12);
    expect(catalog?.fill_kind).toBe("context_quantity");
    expect(catalog?.collection.features[0]?.properties[CONTEXT_FILL_PROPERTY]).toBe(0.12);
    expect(contextFillCount(catalog)).toBe(2);
    const paint = highlightFillPaint(catalog, {
      hoverId: null,
      selectedId: null,
      layerActive: true,
      fitGeneration: 0,
    });
    expect(JSON.stringify(paint["fill-color"])).toContain(CONTEXT_FILL_PROPERTY);
    expect(JSON.stringify(paint["fill-color"])).not.toContain("backend_order");
  });

  it("does not resurrect thermal rank when D8 is withheld and context mode is on", () => {
    const withheld = historical(false);
    expect(withheld.fill_authorized).toBe(false);
    expect(rankedFillCount(withheld)).toBe(0);
    const catalog = bindMapModeCatalog({
      historical: withheld,
      mode: "TREE_CANOPY",
      zones,
    });
    expect(catalogUsesThermalRank(catalog)).toBe(false);
    expect(catalog?.fill_authorized).toBe(false);
    expect(rankedFillCount(catalog)).toBe(0);
    expect(catalog?.zones.every((zone) => zone.relative_order == null)).toBe(true);
    expect(catalog?.zones.every((zone) => zone.q_A_value == null)).toBe(true);
    const paint = highlightFillPaint(catalog, {
      hoverId: null,
      selectedId: null,
      layerActive: true,
      fitGeneration: 0,
    });
    expect(JSON.stringify(paint)).not.toContain("backend_order");
    expect(contextFillCount(catalog)).toBe(2);
  });

  it("leaves MOE-unreliable income without a fill", () => {
    expect(contextFillValue("INCOME", zones[0]!)).toBeNull();
    const catalog = bindMapModeCatalog({
      historical: historical(true),
      mode: "INCOME",
      zones,
    });
    const first = catalog?.collection.features.find((row) => row.properties.GEOID === GEOID);
    const second = catalog?.collection.features.find((row) => row.properties.GEOID === OTHER);
    expect(first?.properties[CONTEXT_FILL_PROPERTY]).toBeNull();
    expect(first?.properties.has_semantic_fill).toBe(false);
    expect(second?.properties[CONTEXT_FILL_PROPERTY]).toBe(55000);
    expect(contextFillCount(catalog)).toBe(1);
  });
});
