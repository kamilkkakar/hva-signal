export type MapMode = "THERMAL" | "TREE_CANOPY" | "INCOME" | "OLDER_HOUSING";

export type QualityStatus =
  | "OBSERVED"
  | "MISSING"
  | "MOE_UNRELIABLE"
  | "SUPPRESSED"
  | "NOT_REQUESTED";

export type MedianComparison = "higher" | "lower" | "similar" | "unknown";

export type ContextFact = {
  kind: string;
  label: string;
  value: number | null;
  unit: string;
  source: string;
  source_year: string;
  comparison: MedianComparison | null;
  comparison_allowed: boolean;
  quality_status: QualityStatus;
  plain_language_sentence: string;
};

export type ZoneMapProperties = {
  zone_id: string;
  census_tract_geoid: string;
  canopy_cover_share: number | null;
  median_household_income: number | null;
  share_pre_1980_housing: number | null;
  canopy_comparison_allowed: boolean;
  income_comparison_allowed: boolean;
  older_housing_comparison_allowed: boolean;
  cooling_site_status: string;
  combined_score_authorized: false;
};

export type AnalysisAreaContextView = {
  area_label: string;
  census_tract_geoid: string;
  thermal_evidence_status: "AVAILABLE" | "UNKNOWN";
  context_facts: ContextFact[];
  preparedness: string[];
  uncertainty_notes: string[];
  direction: string[];
  sources: string[];
  cope_characteristics: string[];
  verify_before_action: string[];
  vulnerability_score_authorized: false;
  combined_score_authorized: false;
};

export type AreaContextDocument = {
  area_id: string;
  area_label: string;
  census_geography: string;
  source_years: { acs: string; canopy: string; cooling_inventory: string };
  metric_quality: Array<{
    kind: string;
    comparison_eligible_count: number;
    comparison_layer_allowed: boolean;
    quantity_only: boolean;
  }>;
  map_modes: MapMode[];
  cooling_inventory: {
    coverage: "partial";
    sites_in_window: number;
    note: string;
  };
  thermal_evidence_status: "AVAILABLE" | "UNKNOWN";
  zones: ZoneMapProperties[];
  selected: AnalysisAreaContextView | null;
  unsupported_questions: string[];
  vulnerability_score_authorized: false;
  combined_score_authorized: false;
};
