import type { AnalysisJobPayload } from "@/api/analysisJobs";

export const REPLAY_0701_GEOMETRY =
  "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f";
export const REPLAY_0701_POLICY =
  "PHX_NORMALIZED_HAZARD_SPREAD_V1_TOP3_BOTTOM3_QA_FLOOR_0P10";
export const REPLAY_0701_RESULT = "THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT";
export const REPLAY_0701_STATISTIC = "TOP3_BOTTOM3_MEAN_DIFFERENCE";
export const REPLAY_0701_JOB_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";

/** 2022-07-01 03:00 phoenix-demo replay — order withheld, long Decision 8 tokens. */
export const replay0701Snapshot: AnalysisJobPayload = {
  job_id: REPLAY_0701_JOB_ID,
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
    system_limitations: [REPLAY_0701_RESULT],
    thermal_differentiation_state: "INSUFFICIENT",
    hazard_spread: {
      policy_version: REPLAY_0701_POLICY,
      reference_version: "PHX_ZTSI_REF_V1",
      zone_geometry_version: REPLAY_0701_GEOMETRY,
      metric: REPLAY_0701_STATISTIC,
      top_group_size: 3,
      floor: 0.1,
      observed_spread: 0.0439665471923536,
      differentiation_state: "INSUFFICIENT",
      reference_quality: "FULL_REFERENCE",
      suppression_reason:
        "normalized hazard spread S is below the frozen Decision 8 floor",
      historical_years: [2020, 2021, 2022],
      reference_hour: "03:00",
    },
    zones: [],
  },
};

export const replay0630Snapshot: AnalysisJobPayload = {
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
    hazard_spread: {
      policy_version: REPLAY_0701_POLICY,
      reference_version: "PHX_ZTSI_REF_V1",
      zone_geometry_version: REPLAY_0701_GEOMETRY,
      metric: REPLAY_0701_STATISTIC,
      top_group_size: 3,
      floor: 0.1,
      observed_spread: 0.22,
      differentiation_state: "SUFFICIENT",
      reference_quality: "FULL_REFERENCE",
      historical_years: [2020, 2021, 2022],
      reference_hour: "03:00",
    },
    zones: [{ zone_id: "04013061000", ranked: true, thermal_ordering_permitted: true }],
  },
};
