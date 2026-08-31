import { describe, expect, it } from "vitest";
import {
  CITIES,
  cityConfig,
  type CityId,
} from "./types";

describe("workspace types", () => {
  it("has exactly four cities", () => {
    expect(CITIES).toHaveLength(4);
  });

  it("Phoenix has local analysis", () => {
    expect(cityConfig("phoenix-az").hasLocalAnalysis).toBe(true);
  });

  it("other cities do not have local analysis", () => {
    const others: CityId[] = ["las-vegas-nv", "tucson-az", "los-angeles-ca"];
    for (const id of others) {
      expect(cityConfig(id).hasLocalAnalysis).toBe(false);
    }
  });

  it("cityConfig returns Phoenix for unknown id", () => {
    expect(cityConfig("unknown" as CityId).id).toBe("phoenix-az");
  });

  it("each city has an apiCityId", () => {
    for (const city of CITIES) {
      expect(city.apiCityId).toBeTruthy();
      expect(typeof city.apiCityId).toBe("string");
    }
  });

  it("city labels use Zone public term (not Census primary)", () => {
    for (const city of CITIES) {
      expect(city.label).not.toContain("Census");
      expect(city.label).not.toContain("Tract");
    }
  });
});
