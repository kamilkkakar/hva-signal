import type { AnalysisJobPayload } from "@/api/analysisJobs";

export const ORACLE_POLICY =
  "PHX_NORMALIZED_HAZARD_SPREAD_V1_TOP3_BOTTOM3_QA_FLOOR_0P10";
export const ORACLE_GEOMETRY =
  "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f";
export const ORACLE_S_SUFFICIENT = 0.13548387096774192;
export const ORACLE_S_INSUFFICIENT = 0.0439665471923536;
export const ORACLE_S_SUFFICIENT_PUBLIC = "0.135";
export const ORACLE_S_INSUFFICIENT_PUBLIC = "0.044";

function zones(count: number, permitted: boolean) {
  return Array.from({ length: count }, (_, index) => ({
    zone_id: String(index + 1).padStart(11, "0"),
    ranked: permitted,
    thermal_ordering_permitted: permitted,
  }));
}

/** 2022-06-30 03:00 — sufficient, 25 ranked fills. */
export const oracle0630Snapshot: AnalysisJobPayload = {
  job_id: "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
  status: "complete",
  request: {
    area_id: "phoenix-demo",
    analysis_time: "2022-06-30T03:00:00",
    analysis_mode: "retrospective",
    horizon_hours: 0,
    lookback_hours: 0,
    granularity_m: 100,
    data_mode: "replay",
  },
  result: {
    thermal_differentiation_state: "SUFFICIENT",
    reference_quality: "FULL_REFERENCE",
    hazard_spread: {
      policy_version: ORACLE_POLICY,
      reference_version: "PHX_ZTSI_REF_V1",
      zone_geometry_version: ORACLE_GEOMETRY,
      metric: "TOP3_BOTTOM3_MEAN_DIFFERENCE",
      top_group_size: 3,
      floor: 0.1,
      observed_spread: ORACLE_S_SUFFICIENT,
      differentiation_state: "SUFFICIENT",
      reference_quality: "FULL_REFERENCE",
      historical_years: [2022, 2023, 2024],
      reference_hour: "03:00",
    },
    zones: zones(25, true),
  },
};

/** 2022-07-01 03:00 — insufficient, 0 ranked fills. */
export const oracle0701Snapshot: AnalysisJobPayload = {
  job_id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
  status: "complete",
  request: {
    area_id: "phoenix-demo",
    analysis_time: "2022-07-01T03:00:00",
    analysis_mode: "retrospective",
    horizon_hours: 0,
    lookback_hours: 0,
    granularity_m: 100,
    data_mode: "replay",
  },
  result: {
    system_limitations: ["THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT"],
    thermal_differentiation_state: "INSUFFICIENT",
    reference_quality: "FULL_REFERENCE",
    hazard_spread: {
      policy_version: ORACLE_POLICY,
      reference_version: "PHX_ZTSI_REF_V1",
      zone_geometry_version: ORACLE_GEOMETRY,
      metric: "TOP3_BOTTOM3_MEAN_DIFFERENCE",
      top_group_size: 3,
      floor: 0.1,
      observed_spread: ORACLE_S_INSUFFICIENT,
      differentiation_state: "INSUFFICIENT",
      reference_quality: "FULL_REFERENCE",
      suppression_reason:
        "normalized hazard spread S is below the frozen Decision 8 floor",
      historical_years: [2022, 2023, 2024],
      reference_hour: "03:00",
    },
    zones: zones(25, false),
  },
};
