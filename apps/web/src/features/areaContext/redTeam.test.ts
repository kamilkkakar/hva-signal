import { describe, expect, it } from "vitest";
import { presentSelectedArea } from "./present";
import type { AnalysisAreaContextView } from "./types";

const blobOf = (view: AnalysisAreaContextView) => {
  const presented = presentSelectedArea(view);
  return [
    presented.notAScore,
    presented.scoreRefusal,
    ...presented.facts.map((fact) => fact.sentence),
    ...presented.preparedness,
    ...presented.uncertainty,
    ...presented.direction,
    ...presented.cope,
  ]
    .join(" ")
    .toLowerCase();
};

const base: AnalysisAreaContextView = {
  area_label: "Phoenix demonstration 25-area analysis window",
  census_tract_geoid: "04013107401",
  thermal_evidence_status: "UNKNOWN",
  context_facts: [],
  preparedness: [
    "1 heat-relief site is identified in the available regional inventory.",
  ],
  uncertainty_notes: [
    "Year built is housing age, not cooling equipment. Air conditioning is not observed.",
  ],
  direction: ["Review cooling access and local response capacity before prioritizing an intervention."],
  sources: [],
  cope_characteristics: [],
  verify_before_action: [],
  vulnerability_score_authorized: false,
  combined_score_authorized: false,
};

describe("area context red team", () => {
  it("rejects score-creep and risk language in the public presenter", () => {
    const blob = blobOf(base);
    expect(blob).not.toMatch(/vulnerability = 78/);
    expect(blob).not.toMatch(/high-risk/);
    expect(blob).not.toMatch(/resilience score/);
    expect(base.vulnerability_score_authorized).toBe(false);
  });

  it("does not say no cooling site or treat a miss as absence", () => {
    const miss: AnalysisAreaContextView = {
      ...base,
      preparedness: [
        "No site was identified in this dataset for this analysis area. This does not establish that no cooling resource exists.",
      ],
    };
    const blob = blobOf(miss);
    expect(blob).not.toMatch(/no cooling site/);
    expect(blob).toMatch(/does not establish that no cooling resource exists/);
  });

  it("does not treat age as individual vulnerability or year built as no AC", () => {
    const blob = blobOf(base);
    expect(blob).not.toMatch(/individual vulnerability/);
    expect(blob).not.toMatch(/no ac/);
    expect(blob).toMatch(/housing age/);
  });

  it("does not ship a thermal placeholder", () => {
    const blob = blobOf(base);
    expect(base.thermal_evidence_status).toBe("UNKNOWN");
    expect(blob).not.toMatch(/referenced separately/);
    expect(blob).not.toMatch(/warrants closer review/);
  });
});
