import { describe, expect, it } from "vitest";
import { globalFillColor, metricDomain, radiusFromPopulation } from "./scale";
import type { CrossCityAreaRecord } from "./types";

const records: CrossCityAreaRecord[] = [
  {
    cityId: "phoenix-az",
    cityLabel: "Phoenix, AZ",
    areaId: "phx-1",
    areaLabel: "Phoenix Area 1",
    metrics: {
      selectedTimeTemperatureC: 40,
      medianHouseholdIncomeUsd: 55_000,
      population: 100_000,
      treeCanopyPct: 8,
    },
  },
  {
    cityId: "las-vegas-nv",
    cityLabel: "Las Vegas, NV",
    areaId: "vegas-1",
    areaLabel: "Las Vegas Area 1",
    metrics: {
      selectedTimeTemperatureC: 42,
      medianHouseholdIncomeUsd: 62_000,
      population: 400_000,
      treeCanopyPct: 18,
    },
  },
];

describe("cross-city scales", () => {
  it("sizes bubbles with sqrt population scaling", () => {
    const domain = metricDomain(records, "population");
    expect(domain).toEqual({ min: 100_000, max: 400_000 });
    const small = radiusFromPopulation(100_000, domain);
    const large = radiusFromPopulation(400_000, domain);
    expect(small).not.toBeNull();
    expect(large).not.toBeNull();
    expect(large).toBeCloseTo((small ?? 0) * 2, 1);
  });

  it("uses one global canopy fill scale", () => {
    const domain = metricDomain(records, "treeCanopyPct");
    expect(globalFillColor(8, domain)).toBe("rgb(233, 245, 237)");
    expect(globalFillColor(18, domain)).toBe("rgb(32, 94, 65)");
    expect(globalFillColor(null, domain)).toBeNull();
  });
});
