import { describe, expect, it } from "vitest";
import { computeSharedTempScale, rangePosition } from "./sharedTempScale";
import type { CrossCityAreaRecord, CrossCityId } from "./types";
import { CROSS_CITY_CITY_ALLOWLIST } from "./types";

describe("sharedTempScale", () => {
  const areas: CrossCityAreaRecord[] = [
    {
      areaId: "a",
      cityId: "phoenix-az",
      cityLabel: "Phoenix, AZ",
      areaLabel: "A",
      metrics: {
        selectedTimeTemperatureC: 40,
        treeCanopyPct: 10,
        medianHouseholdIncomeUsd: 50000,
        olderHousingPct: 40,
        population: 1000,
      },
    },
    {
      areaId: "b",
      cityId: "phoenix-az",
      cityLabel: "Phoenix, AZ",
      areaLabel: "B",
      metrics: {
        selectedTimeTemperatureC: 42,
        treeCanopyPct: 12,
        medianHouseholdIncomeUsd: 52000,
        olderHousingPct: 42,
        population: 1100,
      },
    },
    {
      areaId: "c",
      cityId: "los-angeles-ca",
      cityLabel: "Los Angeles, CA",
      areaLabel: "C",
      metrics: {
        selectedTimeTemperatureC: 30,
        treeCanopyPct: 20,
        medianHouseholdIncomeUsd: 70000,
        olderHousingPct: 50,
        population: 2000,
      },
    },
  ];

  it("uses one shared min/max across cities", () => {
    const ids = CROSS_CITY_CITY_ALLOWLIST.map((c) => c.id) as CrossCityId[];
    const scale = computeSharedTempScale(areas, ids);
    expect(scale).not.toBeNull();
    expect(scale!.minC).toBe(30);
    expect(scale!.maxC).toBe(42);
    const phx = scale!.cities.find((c) => c.cityId === "phoenix-az");
    expect(phx?.minC).toBe(40);
    expect(phx?.maxC).toBe(42);
  });

  it("positions ranges on the shared scale", () => {
    expect(rangePosition(30, 30, 42)).toBe(0);
    expect(rangePosition(42, 30, 42)).toBe(1);
  });
});
