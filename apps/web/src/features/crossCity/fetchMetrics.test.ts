import { describe, expect, it } from "vitest";
import { normalizeCrossCityMetrics } from "./fetchMetrics";

describe("cross-city metrics client", () => {
  it("normalizes flat area rows for the allowlisted cities", () => {
    const payload = normalizeCrossCityMetrics({
      comparison_clock_local: "2024-07-08 15:00",
      areas: [
        {
          city_id: "phoenix-az",
          city_label: "Phoenix, AZ",
          area_id: "phx-1",
          area_label: "Analysis Area 1",
          selected_time_temperature_c: 41.2,
          median_household_income_usd: 58000,
          population: 105000,
          tree_canopy_pct: 12.5,
        },
      ],
    });

    expect(payload.comparisonClockLocal).toBe("2024-07-08 15:00");
    expect(payload.areas).toEqual([
      {
        cityId: "phoenix-az",
        cityLabel: "Phoenix, AZ",
        areaId: "phx-1",
        areaLabel: "Analysis Area 1",
        metrics: {
          selectedTimeTemperatureC: 41.2,
          medianHouseholdIncomeUsd: 58000,
          population: 105000,
          treeCanopyPct: 12.5,
        },
      },
    ]);
  });

  it("normalizes nested city payloads and drops unsupported cities", () => {
    const payload = normalizeCrossCityMetrics({
      cities: [
        {
          city: "Tucson, AZ",
          areas: [
            {
              area_id: "tuc-1",
              area_label: "Tucson Area 1",
              temperature_c: 39,
              median_household_income: 49000,
              population: 85000,
              tree_canopy_percent: null,
            },
          ],
        },
        {
          city: "Chicago, IL",
          areas: [
            {
              area_id: "chi-1",
              area_label: "Chicago Area 1",
              temperature_c: 32,
              median_household_income: 71000,
            },
          ],
        },
      ],
    });

    expect(payload.areas).toHaveLength(1);
    expect(payload.areas[0]?.cityId).toBe("tucson-az");
    expect(payload.areas[0]?.metrics.treeCanopyPct).toBeNull();
  });
});
