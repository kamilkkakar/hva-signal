import { describe, expect, it } from "vitest";
import { interpretContextFact, resolveDominantPattern } from "./pattern";
import { synthesizeNarrative } from "./synthesize";
import type { NarrativeSynthesisInput } from "./types";

function base(overrides: Partial<NarrativeSynthesisInput> = {}): NarrativeSynthesisInput {
  return {
    areaLabel: "Analysis Area 1",
    analysisAreaCount: 25,
    selectedTemperatureC: 33.7,
    observationStamp: "15 Jul 2025 · 03:00",
    spatialDiff: "INSUFFICIENT",
    historicalPosition: {
      status: "UNAVAILABLE",
      percent: null,
      sentence: "Historical position is not available for this observation.",
    },
    matchedChangeC: 1.54,
    geographyMedianChangeC: 1.53,
    matchedNightsTotal: 31,
    observedHighC: 42.3,
    observedHighLabel: "15:00",
    contextComparisons: [
      {
        kind: "canopy_cover_share",
        label: "Tree canopy",
        valueDisplay: "22%",
        comparison: "higher",
        comparisonAllowed: true,
        tone: "weaken",
        interpretation:
          "This does not support a simple low-canopy explanation for the selected thermal pattern.",
      },
    ],
    preparedness: "NOT_IDENTIFIED_IN_DATASET",
    thermalAvailable: true,
    ...overrides,
  };
}

describe("dominant evidence pattern", () => {
  it("selects temporal change when matched delta is meaningful and spatial is insufficient", () => {
    expect(resolveDominantPattern(base())).toBe("TEMPORAL_CHANGE_DOMINATES");
  });

  it("selects spatial present when differentiation is sufficient and temporal is weak", () => {
    expect(
      resolveDominantPattern(
        base({ spatialDiff: "SUFFICIENT", matchedChangeC: 0.1, geographyMedianChangeC: 0.1 }),
      ),
    ).toBe("SPATIAL_DIFFERENTIATION_PRESENT");
  });

  it("selects preparedness gap when thermal evidence is thin and inventory misses", () => {
    expect(
      resolveDominantPattern(
        base({
          thermalAvailable: false,
          selectedTemperatureC: null,
          matchedChangeC: null,
          geographyMedianChangeC: null,
          observedHighC: null,
          contextComparisons: [],
          preparedness: "NOT_IDENTIFIED_IN_DATASET",
        }),
      ),
    ).toBe("PREPAREDNESS_GAP_REQUIRES_VERIFICATION");
  });

  it("selects insufficient evidence when almost nothing is bound", () => {
    expect(
      resolveDominantPattern(
        base({
          thermalAvailable: false,
          selectedTemperatureC: null,
          matchedChangeC: null,
          geographyMedianChangeC: null,
          observedHighC: null,
          contextComparisons: [],
          preparedness: "UNAVAILABLE",
          spatialDiff: "UNKNOWN",
        }),
      ),
    ).toBe("INSUFFICIENT_EVIDENCE");
  });

  it("selects context investigation when only context comparisons remain", () => {
    expect(
      resolveDominantPattern(
        base({
          thermalAvailable: false,
          selectedTemperatureC: null,
          matchedChangeC: null,
          geographyMedianChangeC: null,
          observedHighC: null,
          preparedness: "UNKNOWN",
          spatialDiff: "UNKNOWN",
        }),
      ),
    ).toBe("CONTEXT_WARRANTS_INVESTIGATION");
  });
});

describe("synthesizeNarrative", () => {
  it("builds Part-15 quality temporal synthesis without trend or score language", () => {
    const story = synthesizeNarrative(base());
    expect(story.dominantPattern).toBe("TEMPORAL_CHANGE_DOMINATES");
    expect(story.patternTitle).toMatch(/temporal change/i);
    expect(story.evidenceSummary.some((row) => row.id === "matched")).toBe(true);
    expect(story.whatEvidenceShows.join(" ")).toMatch(/1\.54 °C higher/);
    expect(story.whatEvidenceShows.join(" ")).toMatch(/too small to support/);
    expect(story.whyItMatters.join(" ")).toMatch(/hottest neighborhood/);
    expect(story.verifyNext.join(" ")).toMatch(/cooling access/i);
    const blob = JSON.stringify(story).toLowerCase();
    expect(blob).not.toMatch(/warming trend|climate trend|vulnerability score|priority score/);
    expect(blob).not.toMatch(/intervention recommendation|no row/);
  });

  it("changes story when spatial evidence becomes sufficient", () => {
    const temporal = synthesizeNarrative(base());
    const spatial = synthesizeNarrative(
      base({ spatialDiff: "SUFFICIENT", matchedChangeC: 0.12, geographyMedianChangeC: 0.1 }),
    );
    expect(temporal.dominantPattern).not.toBe(spatial.dominantPattern);
    expect(spatial.whatEvidenceShows.join(" ")).toMatch(/spatial comparison/i);
    expect(spatial.verifyNext.join(" ")).toMatch(/spatial comparison/i);
  });

  it("does not tell a verify-none story when preparedness is identified", () => {
    const story = synthesizeNarrative(base({ preparedness: "IDENTIFIED" }));
    expect(story.whatEvidenceShows.join(" ")).toMatch(/identified in the available inventory/i);
    expect(story.verifyNext.join(" ")).toMatch(/confirm hours/i);
    expect(story.verifyNext.join(" ")).not.toMatch(/no heat-relief site/i);
  });

  it("keeps uncertain context out of directional claims", () => {
    const story = synthesizeNarrative(
      base({
        contextComparisons: [
          {
            kind: "share_age_65_plus",
            label: "Age 65+",
            valueDisplay: "12%",
            comparison: null,
            comparisonAllowed: false,
            tone: "uncertain",
            interpretation:
              "Estimate shown with uncertainty; a geography comparison is not published.",
          },
        ],
      }),
    );
    expect(story.whatEvidenceShows.join(" ")).not.toMatch(/Age 65\+ is above/);
  });
});

describe("interpretContextFact", () => {
  it("weakens a low-canopy story when canopy is above median", () => {
    const result = interpretContextFact({
      kind: "canopy_cover_share",
      comparison: "higher",
      comparisonAllowed: true,
    });
    expect(result.tone).toBe("weaken");
    expect(result.interpretation).toMatch(/does not support a simple low-canopy/i);
  });
});
