import { describe, expect, it } from "vitest";
import {
  CROSS_CITY_CITY_ALLOWLIST,
  CROSS_CITY_COMPARISON_CLOCK_LOCAL,
  CROSS_CITY_DEFAULT_ENCODINGS,
} from "./types";

describe("cross-city defaults", () => {
  it("keeps the fixed four-city allowlist", () => {
    expect(CROSS_CITY_CITY_ALLOWLIST.map((city) => city.label)).toEqual([
      "Phoenix, AZ",
      "Las Vegas, NV",
      "Tucson, AZ",
      "Los Angeles, CA",
    ]);
  });

  it("keeps the fixed comparison clock and default encodings", () => {
    expect(CROSS_CITY_COMPARISON_CLOCK_LOCAL).toBe("2024-07-08 15:00");
    expect(CROSS_CITY_DEFAULT_ENCODINGS).toEqual({
      x: "treeCanopyPct",
      y: "selectedTimeTemperatureC",
      size: "population",
      fill: "treeCanopyPct",
    });
  });
});
