import { describe, expect, it } from "vitest";
import { deriveHistoricalFindings, deriveThermalFindings } from "./derivedFindings";

describe("deriveThermalFindings", () => {
  it("computes highest/lowest/span/pairwise from observations", () => {
    const findings = deriveThermalFindings([
      { id: "a", label: "Night A", temperatureC: 30 },
      { id: "b", label: "Night B", temperatureC: 34.5 },
      { id: "c", label: "Night C", temperatureC: 32 },
    ]);
    expect(findings.highest?.id).toBe("b");
    expect(findings.lowest?.id).toBe("a");
    expect(findings.spanC).toBeCloseTo(4.5);
    expect(findings.pairwise).toHaveLength(2);
    expect(findings.pairwise[0]?.deltaC).toBeCloseTo(4.5);
    expect(findings.latestVsEarliestC).toBeCloseTo(2);
  });

  it("returns empty pairwise for a single observation (no invented gaps)", () => {
    const findings = deriveThermalFindings([
      { id: "only", label: "Live", temperatureC: 41.2 },
    ]);
    expect(findings.count).toBe(1);
    expect(findings.pairwise).toEqual([]);
    expect(findings.spanC).toBe(0);
    expect(findings.latestVsEarliestC).toBe(0);
  });
});

describe("deriveHistoricalFindings", () => {
  it("labels latest-vs-earliest from year values", () => {
    const findings = deriveHistoricalFindings({
      years: [
        { year: 2022, meanC: 33 },
        { year: 2023, meanC: 34 },
        { year: 2024, meanC: 35.5 },
      ],
      medianChangeC: 1.2,
      matchedNightCount: 31,
    });
    expect(findings.latestVsEarliestC).toBeCloseTo(2.5);
    expect(findings.geographyMedianChangeC).toBeCloseTo(1.2);
    expect(findings.matchedNightCount).toBe(31);
  });
});
