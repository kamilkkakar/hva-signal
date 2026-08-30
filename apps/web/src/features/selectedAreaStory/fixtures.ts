import type { AnalysisResultStub } from "@/api/analysisJobs";
import type { AnalysisAreaContextView, AreaContextDocument, ContextFact } from "@/features/areaContext/types";

export const AREA_1 = "04013107401";
export const AREA_25 = "04013108400";
export const MISSING_GEOID = "04013999999";

export function fact(overrides: Partial<ContextFact> & Pick<ContextFact, "kind" | "label">): ContextFact {
  return {
    value: 0.2,
    unit: "percent of plantable ground",
    source: "ACS",
    source_year: "2024",
    comparison: "lower",
    comparison_allowed: true,
    quality_status: "OBSERVED",
    plain_language_sentence: `${overrides.label} quantity.`,
    ...overrides,
  };
}

export function contextView(
  overrides: Partial<AnalysisAreaContextView> = {},
): AnalysisAreaContextView {
  return {
    area_label: "Phoenix demonstration 25-area analysis window",
    census_tract_geoid: AREA_1,
    thermal_evidence_status: "UNKNOWN",
    context_facts: [
      fact({
        kind: "canopy_cover_share",
        label: "Tree canopy",
        value: 0.15,
        unit: "percent of plantable ground",
        source: "shade study",
        source_year: "2022",
      }),
      fact({
        kind: "median_household_income",
        label: "Median household income",
        value: 52000,
        unit: "USD",
        comparison: "lower",
      }),
      fact({
        kind: "share_pre_1980_housing",
        label: "Homes built before 1980",
        value: 0.41,
        unit: "percent of homes",
      }),
      fact({
        kind: "share_one_person_household",
        label: "One-person households",
        value: 0.33,
        unit: "percent of households",
      }),
    ],
    preparedness: [
      "No site was identified in this dataset for this analysis area. This does not establish that no cooling resource exists.",
    ],
    uncertainty_notes: [
      "Year built is housing age, not cooling equipment. Air conditioning is not observed.",
    ],
    direction: [],
    sources: ["ACS 5-year 2020-2024"],
    cope_characteristics: [],
    verify_before_action: [],
    vulnerability_score_authorized: false,
    combined_score_authorized: false,
    ...overrides,
  };
}

export function sufficientResult(geoid = AREA_1): AnalysisResultStub {
  return {
    thermal_differentiation_state: "SUFFICIENT",
    zones: [
      {
        zone_id: geoid,
        ranked: true,
        thermal_ordering_permitted: true,
        q_A: 0.812,
      },
    ],
  };
}

export function withheldResult(geoid = AREA_1): AnalysisResultStub {
  return {
    thermal_differentiation_state: "INSUFFICIENT",
    system_limitations: ["THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT"],
    zones: [
      {
        zone_id: geoid,
        ranked: false,
        thermal_ordering_permitted: false,
        q_A: 0.812,
      },
    ],
  };
}

export function documentFor(view: AnalysisAreaContextView): AreaContextDocument {
  return {
    area_id: "phoenix-demo",
    area_label: view.area_label,
    census_geography: "census tract (11-digit GEOID)",
    source_years: { acs: "ACS 5-year 2020-2024", canopy: "2022", cooling_inventory: "2026-05-05" },
    metric_quality: [],
    comparison_eligibility: { canopy_cover_share: 25 },
    map_modes: ["THERMAL", "TREE_CANOPY", "INCOME", "OLDER_HOUSING"],
    cooling_inventory: {
      coverage: "partial",
      sites_in_window: 4,
      note: "Partial regional inventory.",
    },
    thermal_evidence_status: "UNKNOWN",
    zones: [
      {
        zone_id: view.census_tract_geoid,
        census_tract_geoid: view.census_tract_geoid,
        canopy_cover_share: 0.15,
        median_household_income: 52000,
        share_pre_1980_housing: 0.41,
        canopy_comparison_allowed: true,
        income_comparison_allowed: true,
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
}
