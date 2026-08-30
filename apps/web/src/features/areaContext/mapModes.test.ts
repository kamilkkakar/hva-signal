import { describe, expect, it } from "vitest";
import { contextFillValue, layerLooksLikeProbability, MAP_MODES } from "./mapModes";
import type { ZoneMapProperties } from "./types";

const props: ZoneMapProperties = {
  zone_id: "04013107401",
  census_tract_geoid: "04013107401",
  canopy_cover_share: 0.12,
  median_household_income: 41000,
  share_pre_1980_housing: 0.33,
  canopy_comparison_allowed: true,
  income_comparison_allowed: false,
  older_housing_comparison_allowed: true,
  cooling_site_status: "IDENTIFIED",
  combined_score_authorized: false,
};

describe("context map modes", () => {
  it("exposes only the four candidate modes", () => {
    expect(MAP_MODES).toEqual(["THERMAL", "TREE_CANOPY", "INCOME", "OLDER_HOUSING"]);
  });

  it("does not color income when comparison is not allowed", () => {
    expect(contextFillValue("INCOME", props)).toBeNull();
    expect(contextFillValue("TREE_CANOPY", props)).toBe(0.12);
    expect(contextFillValue("THERMAL", props)).toBeNull();
  });

  it("does not treat context fills as probability or risk", () => {
    expect(layerLooksLikeProbability("TREE_CANOPY")).toBe(false);
    expect(layerLooksLikeProbability("INCOME")).toBe(false);
    expect(layerLooksLikeProbability("OLDER_HOUSING")).toBe(false);
  });
});
