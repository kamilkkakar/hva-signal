/**
 * Bubble plot quality helpers for cross-city explorer.
 * AREA ∝ population via radius = k * sqrt(population).
 */

import { describe, expect, it } from "vitest";
import { globalFillColor, metricDomain, radiusFromPopulation } from "./scale";
import type { CrossCityAreaRecord } from "./types";
import { presentBubbleExplorer } from "./BubbleExplorer";

function record(
  partial: Partial<CrossCityAreaRecord> & Pick<CrossCityAreaRecord, "areaId" | "cityId">,
): CrossCityAreaRecord {
  return {
    cityLabel: partial.cityLabel ?? partial.cityId,
    areaLabel: partial.areaLabel ?? partial.areaId,
    metrics: {
      selectedTimeTemperatureC: partial.metrics?.selectedTimeTemperatureC ?? null,
      medianHouseholdIncomeUsd: partial.metrics?.medianHouseholdIncomeUsd ?? 50000,
      population: partial.metrics?.population ?? 1000,
      treeCanopyPct: partial.metrics?.treeCanopyPct ?? 5,
    },
    ...partial,
  };
}

describe("cross-city bubble data quality", () => {
  it("scales bubble area with population (radius ∝ sqrt)", () => {
    const domain = { min: 100, max: 10000 };
    const rSmall = radiusFromPopulation(100, domain)!;
    const rLarge = radiusFromPopulation(10000, domain)!;
    expect(rLarge / rSmall).toBeCloseTo(10, 5);
    expect((rLarge * rLarge) / (rSmall * rSmall)).toBeCloseTo(100, 5);
  });

  it("uses one global canopy fill scale across cities", () => {
    const records = [
      record({
        cityId: "phoenix-az",
        areaId: "a",
        metrics: {
          selectedTimeTemperatureC: 40,
          medianHouseholdIncomeUsd: 1,
          population: 1,
          treeCanopyPct: 2,
        },
      }),
      record({
        cityId: "los-angeles-ca",
        areaId: "b",
        metrics: {
          selectedTimeTemperatureC: 30,
          medianHouseholdIncomeUsd: 2,
          population: 2,
          treeCanopyPct: 2,
        },
      }),
    ];
    const domain = metricDomain(records, "treeCanopyPct");
    expect(globalFillColor(2, domain)).toEqual(globalFillColor(2, domain));
    expect(globalFillColor(2, domain)).toEqual(
      globalFillColor(records[1]!.metrics.treeCanopyPct, domain),
    );
  });

  it("keeps city outline while fill is missing", () => {
    const records = [
      record({
        cityId: "tucson-az",
        areaId: "t1",
        metrics: {
          selectedTimeTemperatureC: 35,
          medianHouseholdIncomeUsd: 40000,
          population: 2000,
          treeCanopyPct: null,
        },
      }),
    ];
    const view = presentBubbleExplorer(records, ["tucson-az"], "tucson-az");
    expect(view.plotted).toHaveLength(1);
    expect(view.plotted[0]!.fillMissing).toBe(true);
    expect(view.plotted[0]!.outline).toMatch(/^#/);
    expect(view.plotted[0]!.fill).toContain("missing-fill");
  });

  it("omits areas when selected-time temperature is missing", () => {
    const records = [
      record({
        cityId: "phoenix-az",
        areaId: "p1",
        metrics: {
          selectedTimeTemperatureC: null,
          medianHouseholdIncomeUsd: 50000,
          population: 3000,
          treeCanopyPct: 1,
        },
      }),
    ];
    const view = presentBubbleExplorer(records, ["phoenix-az"], "phoenix-az");
    expect(view.plotted).toHaveLength(0);
    expect(view.omittedCount).toBe(1);
  });
});
