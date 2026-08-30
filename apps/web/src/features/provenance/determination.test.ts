import { describe, expect, it } from "vitest";
import type { AnalysisJobPayload } from "@/api/analysisJobs";
import {
  formatPublicPolicyRequirement,
  formatPublicSeparation,
  formatYearSpan,
  howDeterminedFromJob,
  spatialDifferentiationPlain,
} from "./determination";

const SUFFICIENT_S = 0.13548387096774192;
const INSUFFICIENT_S = 0.0439665471923536;

function sufficientJob(overrides: Partial<AnalysisJobPayload> = {}): AnalysisJobPayload {
  return {
    job_id: "job-sufficient",
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
        policy_version: "PHX_NORMALIZED_HAZARD_SPREAD_V1_TOP3_BOTTOM3_QA_FLOOR_0P10",
        reference_version: "PHX_ZTSI_REF_V1__LONG",
        zone_geometry_version:
          "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f",
        metric: "TOP3_BOTTOM3_MEAN_DIFFERENCE",
        floor: 0.1,
        observed_spread: SUFFICIENT_S,
        differentiation_state: "SUFFICIENT",
        historical_years: [2022, 2023, 2024],
        reference_hour: "03:00",
      },
    },
    ...overrides,
  };
}

describe("public determination precision", () => {
  it("prints observed separation at 4 decimals, not 17", () => {
    expect(formatPublicSeparation(SUFFICIENT_S)).toBe("0.1355");
    expect(formatPublicSeparation(INSUFFICIENT_S)).toBe("0.0440");
    expect(formatPublicSeparation(SUFFICIENT_S)).not.toContain("0.135483870967741");
  });

  it("prints the policy floor as 0.10", () => {
    expect(formatPublicPolicyRequirement(0.1)).toBe("0.10");
    expect(formatPublicPolicyRequirement(0.1)).not.toMatch(/%|q_A/);
  });

  it("spans historical years with an en dash", () => {
    expect(formatYearSpan([2022, 2023, 2024])).toBe("2022–2024");
  });

  it("uses Supported / Withheld, not SUFFICIENT / INSUFFICIENT", () => {
    expect(spatialDifferentiationPlain("SUFFICIENT")).toBe("Supported");
    expect(spatialDifferentiationPlain("INSUFFICIENT")).toBe("Withheld");
    expect(spatialDifferentiationPlain("READY")).toBeNull();
  });
});

describe("howDeterminedFromJob", () => {
  it("projects the 2022-06-30 sufficient public facts", () => {
    const view = howDeterminedFromJob(sufficientJob());
    expect(view).toEqual({
      historicalComparison: "2022–2024 at 03:00",
      spatialDifferentiation: "Supported",
      observedSeparation: "0.1355",
      policyRequirement: "0.10",
      observedSeparationExact: SUFFICIENT_S,
    });
  });

  it("projects withheld when differentiation is insufficient", () => {
    const view = howDeterminedFromJob(
      sufficientJob({
        result: {
          thermal_differentiation_state: "INSUFFICIENT",
          hazard_spread: {
            floor: 0.1,
            observed_spread: INSUFFICIENT_S,
            differentiation_state: "INSUFFICIENT",
            historical_years: [2022, 2023, 2024],
            reference_hour: "03:00",
          },
        },
      }),
    );
    expect(view?.spatialDifferentiation).toBe("Withheld");
    expect(view?.observedSeparation).toBe("0.0440");
  });

  it("returns null before a hazard-spread result exists", () => {
    expect(howDeterminedFromJob(null)).toBeNull();
    expect(
      howDeterminedFromJob({
        job_id: "idle",
        status: "queued",
        request: {
          area_id: "phoenix-demo",
          analysis_time: "2022-06-30T03:00:00",
          analysis_mode: "retrospective",
          horizon_hours: 0,
          lookback_hours: 0,
          granularity_m: 100,
          data_mode: "replay",
        },
      }),
    ).toBeNull();
  });
});
