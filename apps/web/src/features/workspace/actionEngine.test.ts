import { describe, expect, it } from "vitest";
import { buildStoryActions, contextHighlights } from "./actionEngine";
import type { ContextComparison } from "@/features/experience/narrative";

describe("actionEngine", () => {
  const comparisons: ContextComparison[] = [
    {
      kind: "canopy_cover_share",
      label: "Tree canopy",
      valueDisplay: "12%",
      comparison: "lower",
      comparisonAllowed: true,
      tone: "strengthen",
      interpretation: null,
    },
    {
      kind: "older_housing_share",
      label: "Older housing",
      valueDisplay: "40%",
      comparison: "higher",
      comparisonAllowed: true,
      tone: "strengthen",
      interpretation: null,
    },
  ];

  it("returns at most 3 actions with why-shown", () => {
    const actions = buildStoryActions({
      comparisons,
      preparedness: "NOT_IDENTIFIED_IN_DATASET",
      spatialSupported: false,
      isPhoenix: true,
    });
    expect(actions.length).toBeLessThanOrEqual(3);
    expect(actions[0]?.id).toBe("verify-cooling");
    expect(actions.every((a) => a.whyShown.length > 0)).toBe(true);
  });

  it("skips above/below when comparison not allowed", () => {
    const lines = contextHighlights(
      [
        {
          kind: "canopy_cover_share",
          label: "Tree canopy",
          valueDisplay: "12%",
          comparison: "lower",
          comparisonAllowed: false,
          tone: "uncertain",
          interpretation: null,
        },
      ],
      "IDENTIFIED",
    );
    expect(lines).toEqual([]);
  });

  it("highlights lower canopy and cooling gap", () => {
    const lines = contextHighlights(comparisons, "UNKNOWN");
    expect(lines).toContain("Lower canopy than comparison median");
    expect(lines).toContain("Higher share of older housing");
    expect(lines).toContain("Cooling resource not identified in available inventory");
  });
});
