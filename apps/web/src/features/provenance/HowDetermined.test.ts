import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { AnalysisJobPayload } from "@/api/analysisJobs";
import { HowDetermined } from "./HowDetermined";

const SUFFICIENT_S = 0.13548387096774192;
const GEOMETRY =
  "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f";
const POLICY = "PHX_NORMALIZED_HAZARD_SPREAD_V1_TOP3_BOTTOM3_QA_FLOOR_0P10";

const sufficient: AnalysisJobPayload = {
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
      policy_version: POLICY,
      reference_version: "PHX_ZTSI_REF_V1__LONG",
      zone_geometry_version: GEOMETRY,
      metric: "TOP3_BOTTOM3_MEAN_DIFFERENCE",
      floor: 0.1,
      observed_spread: SUFFICIENT_S,
      differentiation_state: "SUFFICIENT",
      historical_years: [2022, 2023, 2024],
      reference_hour: "03:00",
    },
  },
};

describe("HowDetermined", () => {
  it("renders the four primary facts without policy, reference, or geometry IDs", () => {
    const html = renderToStaticMarkup(
      createElement(HowDetermined, { snapshot: sufficient }),
    );
    expect(html).toContain('data-testid="how-this-was-determined"');
    expect(html).toContain("How this was determined");
    expect(html).toContain("2022–2024 at 03:00");
    expect(html).toContain("Supported");
    expect(html).toContain("0.1355");
    expect(html).toContain("0.10");
    expect(html).not.toContain("0.135483870967741");
    expect(html).not.toContain(POLICY);
    expect(html).not.toContain(GEOMETRY);
    expect(html).not.toContain("TOP3_BOTTOM3");
    expect(html).not.toContain("PHX_ZTSI_REF");
    expect(html).not.toContain("SUFFICIENT");
    expect(html).not.toContain("q_A");
    expect(html).not.toContain("Decision 8");
    expect(html).not.toContain("source-tape");
  });

  it("renders nothing before a determination exists", () => {
    expect(renderToStaticMarkup(createElement(HowDetermined, { snapshot: null }))).toBe(
      "",
    );
  });
});
