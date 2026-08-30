import { describe, expect, it } from "vitest";
import { SCORE_QUESTION } from "./copy";
import { answersProductQuestions, presentList, presentSelectedArea } from "./present";
import type { AnalysisAreaContextView, AreaContextDocument } from "./types";

const view: AnalysisAreaContextView = {
  area_label: "Phoenix demonstration 25-area analysis window",
  census_tract_geoid: "04013107401",
  thermal_evidence_status: "UNKNOWN",
  context_facts: [
    {
      kind: "canopy_cover_share",
      label: "Tree canopy",
      value: 0.15,
      unit: "percent of plantable ground",
      source: "shade study",
      source_year: "2022",
      comparison: "lower",
      comparison_allowed: true,
      quality_status: "OBSERVED",
      plain_language_sentence:
        "Tree canopy covers 15% of plantable ground in this analysis area. That is below the median of the selected 25-area geography.",
    },
  ],
  preparedness: [
    "No site was identified in this dataset for this analysis area. This does not establish that no cooling resource exists.",
  ],
  uncertainty_notes: ["Year built is housing age, not cooling equipment. Air conditioning is not observed."],
  direction: ["Review cooling access and local response capacity before prioritizing an intervention."],
  sources: ["ACS 5-year 2020-2024"],
  cope_characteristics: [
    "This analysis area also has lower tree canopy than the selected-area median.",
  ],
  verify_before_action: [
    "Review cooling access and local response capacity before prioritizing an intervention.",
  ],
  vulnerability_score_authorized: false,
  combined_score_authorized: false,
};

const document: AreaContextDocument = {
  area_id: "phoenix-demo",
  area_label: view.area_label,
  census_geography: "census tract (11-digit GEOID)",
  source_years: { acs: "ACS 5-year 2020-2024", canopy: "2022", cooling_inventory: "2026-05-05" },
  metric_quality: [
    {
      kind: "canopy_cover_share",
      comparison_eligible_count: 25,
      comparison_layer_allowed: true,
      quantity_only: false,
    },
    {
      kind: "poverty_rate",
      comparison_eligible_count: 0,
      comparison_layer_allowed: false,
      quantity_only: true,
    },
  ],
  map_modes: ["THERMAL", "TREE_CANOPY", "INCOME", "OLDER_HOUSING"],
  cooling_inventory: {
    coverage: "partial",
    sites_in_window: 4,
    note: "This does not establish that no cooling resource exists.",
  },
  thermal_evidence_status: "UNKNOWN",
  zones: [
    {
      zone_id: "04013107401",
      census_tract_geoid: "04013107401",
      canopy_cover_share: 0.15,
      median_household_income: null,
      share_pre_1980_housing: 0.4,
      canopy_comparison_allowed: true,
      income_comparison_allowed: false,
      older_housing_comparison_allowed: true,
      cooling_site_status: "NOT_IDENTIFIED_IN_DATASET",
      combined_score_authorized: false,
    },
  ],
  selected: view,
  unsupported_questions: ["What is the vulnerability score?"],
  vulnerability_score_authorized: false,
  combined_score_authorized: false,
};

describe("area context presentation", () => {
  it("presents selected-area quantity language and refuses a score", () => {
    const presented = presentSelectedArea(view);
    expect(presented.facts[0]?.sentence).toContain("plantable ground");
    expect(presented.notAScore).toMatch(/not a vulnerability score/i);
    expect(presented.thermalStatus).toBe("UNKNOWN");
    expect(presented.preparedness.join(" ")).not.toMatch(/no cooling site/i);
  });

  it("answers cope and verify questions and refuses a vulnerability score", () => {
    const answers = answersProductQuestions(view);
    expect(answers[SCORE_QUESTION]).toBe(false);
    expect(answers["What should a city verify before taking action?"][0]).toMatch(/verify|review/i);
    expect(
      answers[
        "What characteristics of this analysis area may reduce its ability to cope with sustained heat?"
      ][0],
    ).toContain("tree canopy");
  });

  it("lists comparison-eligible values only", () => {
    const rows = presentList(document);
    expect(rows[0]?.canopy).toBe(0.15);
    expect(rows[0]?.income).toBeNull();
  });
});
