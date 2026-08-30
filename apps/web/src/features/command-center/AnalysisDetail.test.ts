import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { AnalysisJobPayload } from "@/api/analysisJobs";
import { AnalysisDetailView } from "./AnalysisDetail";
import { DecisionRailView } from "./DecisionRail";

const GEOMETRY =
  "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f";
const POLICY =
  "PHX_NORMALIZED_HAZARD_SPREAD_V1_TOP3_BOTTOM3_QA_FLOOR_0P10";
const RESULT = "THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT";
const JOB_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";

const completeSnapshot: AnalysisJobPayload = {
  job_id: JOB_ID,
  status: "complete",
  result: {
    system_limitations: [RESULT],
    hazard_spread: {
      policy_version: POLICY,
      reference_version: "PHX_ZTSI_REF_V1",
      zone_geometry_version: GEOMETRY,
      metric: "TOP3_BOTTOM3_MEAN_DIFFERENCE",
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

describe("AnalysisDetail overflow surface", () => {
  it("moves long Decision 8 analysis into a full-width open accordion", () => {
    const html = renderToStaticMarkup(
      createElement(AnalysisDetailView, { snapshot: completeSnapshot }),
    );
    expect(html).toContain('data-testid="analysis-detail"');
    expect(html).toMatch(/<details[^>]*\sopen/);
    expect(html).toContain("Analysis detail");
    expect(html).toContain('data-testid="decision8-evidence-panel"');
    expect(html).toContain(POLICY);
    expect(html).toContain(GEOMETRY);
    expect(html).toContain(RESULT);
    expect(html).toContain('data-testid="decision8-policy-token-copy"');
    expect(html).toContain('data-testid="decision8-geometry-token-copy"');
    expect(html).toContain(`data-full-value="${POLICY}"`);
    expect(html).not.toMatch(/fortyguard/i);
  });

  it("stays closed when no result has arrived", () => {
    const html = renderToStaticMarkup(
      createElement(AnalysisDetailView, { snapshot: null }),
    );
    expect(html).toContain('data-testid="analysis-detail"');
    expect(html).not.toMatch(/<details[^>]*\sopen/);
  });
});

describe("DecisionRail overflow surface", () => {
  it("keeps the third column short and copies the job id", () => {
    const html = renderToStaticMarkup(
      createElement(DecisionRailView, {
        ranking: { state: "INSUFFICIENT_EVIDENCE", scores: [] },
        snapshot: completeSnapshot,
        busy: false,
        canResubmit: false,
        stalled: false,
        lastRequest: null,
        onResubmit: () => undefined,
      }),
    );
    expect(html).toContain('data-testid="job-id-copy"');
    expect(html).toContain(JOB_ID);
    expect(html).toContain("Analysis detail below");
    expect(html).not.toContain('data-testid="decision8-evidence-panel"');
    expect(html).not.toContain(GEOMETRY);
  });
});
