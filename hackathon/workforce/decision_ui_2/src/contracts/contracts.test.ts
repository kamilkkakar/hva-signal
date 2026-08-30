import { describe, expect, it } from "vitest";
import {
  ANALYSIS_AREA_COUNT,
  CHART_KINDS,
  MAP_MODE_IDS,
  QUESTION_IDS,
  analysisAreaLabel,
  buildAnalysisAreas,
  isPending,
  pendingTemporal,
} from "./index";

describe("contracts", () => {
  it("keeps 25 analysis areas with primary labels", () => {
    const areas = buildAnalysisAreas();
    expect(areas).toHaveLength(ANALYSIS_AREA_COUNT);
    expect(areas[0]?.primaryLabel).toBe(analysisAreaLabel(1));
    expect(areas.every((area) => area.censusTractGeoid === null)).toBe(true);
  });

  it("covers the required question, map, and chart sets", () => {
    expect(QUESTION_IDS).toHaveLength(8);
    expect(MAP_MODE_IDS).toHaveLength(8);
    expect(CHART_KINDS).toEqual([
      "hourly_curve",
      "monthly_trend",
      "seasonal_comparison",
      "year_over_year",
      "cumulative_anomaly",
      "persistence",
      "treated_vs_comparison",
    ]);
  });

  it("marks unbound temporal fields as pending", () => {
    const field = pendingTemporal<number>("awaiting bind");
    expect(isPending(field)).toBe(true);
    expect(field.value).toBeNull();
  });
});
