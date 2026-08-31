import { describe, expect, it } from "vitest";
import {
  CROSS_CITY_CANOPY_DISPLAY_SCALE_V1,
  canopyDisplayDomain,
} from "./canopyDisplayScale";
import { metricDomain, radiusFromPopulation } from "./scale";
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
      olderHousingPct: 40,
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
      olderHousingPct: 55,
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

  it("uses fixed CROSS_CITY_CANOPY_DISPLAY_SCALE_V1, not visible-city stretch", () => {
    expect(CROSS_CITY_CANOPY_DISPLAY_SCALE_V1.domainMin).toBe(0);
    expect(CROSS_CITY_CANOPY_DISPLAY_SCALE_V1.domainMax).toBe(25);
    expect(metricDomain(records, "treeCanopyPct")).toEqual(canopyDisplayDomain());
    expect(metricDomain(records, "treeCanopyPct")).not.toEqual({ min: 8, max: 18 });
  });
});
