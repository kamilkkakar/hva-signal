import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { AnalysisJobPayload } from "@/api/analysisJobs";
import { ProvenanceBand } from "./ProvenanceBand";

const SUFFICIENT_S = 0.13548387096774192;
const GEOMETRY =
  "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f";
const POLICY = "PHX_NORMALIZED_HAZARD_SPREAD_V1_TOP3_BOTTOM3_QA_FLOOR_0P10";
const STATISTIC = "TOP3_BOTTOM3_MEAN_DIFFERENCE";

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
    data_status: "replay",
    thermal_source: "replay",
    thermal_differentiation_state: "SUFFICIENT",
    hazard_spread: {
      policy_version: POLICY,
      reference_version: "PHX_ZTSI_REF_V1__LONG",
      zone_geometry_version: GEOMETRY,
      metric: STATISTIC,
      floor: 0.1,
      observed_spread: SUFFICIENT_S,
      differentiation_state: "SUFFICIENT",
      historical_years: [2022, 2023, 2024],
      reference_hour: "03:00",
    },
    evidence_graph: { nodes: [{ id: "n1" }], edges: [] },
    zones: [{ zone_id: "04013061000", thermal_ordering_permitted: true }],
  },
};

function sectionHtml(html: string, testId: string): string {
  const start = html.indexOf(`data-testid="${testId}"`);
  if (start < 0) {
    return "";
  }
  const from = html.slice(start);
  const close = from.search(/<\/(section|details)>/);
  return close < 0 ? from : from.slice(0, close);
}

describe("ProvenanceBand disclosure IA", () => {
  it("puts public facts first and keeps every technical ID in Advanced", () => {
    const html = renderToStaticMarkup(createElement(ProvenanceBand, { snapshot: sufficient }));
    expect(html).toContain('data-testid="how-this-was-determined"');
    expect(html).toContain('data-testid="command-center-provenance-header"');
    expect(html).toContain('data-testid="public-provenance-experience"');
    expect(html).toContain('data-testid="advanced-technical-details"');
    expect(html).toContain('data-testid="analysis-detail"');
    expect(html).toContain("Advanced technical details");
    expect(html.indexOf("how-this-was-determined")).toBeLessThan(
      html.indexOf("advanced-technical-details"),
    );

    const primary = sectionHtml(html, "how-this-was-determined");
    expect(primary).toContain("2022–2024 at 03:00");
    expect(primary).toContain("Supported");
    expect(primary).toContain("0.1355");
    expect(primary).toContain("0.10");
    expect(primary).not.toContain(POLICY);
    expect(primary).not.toContain(GEOMETRY);
    expect(primary).not.toContain(STATISTIC);
    expect(primary).not.toContain("0.135483870967741");

    const advanced = html.slice(html.indexOf('data-testid="analysis-detail"'));
    expect(advanced).toContain(POLICY);
    expect(html).toContain(GEOMETRY);
    expect(html).toContain(STATISTIC);
    expect(html).toContain("0.135483870967741");
    expect(html).toContain('data-testid="decision8-policy-token-copy"');
    expect(html).toContain('data-testid="decision8-reference-token-copy"');
    expect(html).toContain('data-testid="decision8-geometry-token-copy"');
    expect(html).toContain('data-testid="decision8-statistic-copy"');
    expect(html).toContain('data-testid="evidence-graph-state-token-copy"');
    expect(html).toContain("GRAPH_POPULATED");
    expect(html).not.toContain("source-tape");
    expect(html).not.toContain('data-testid="source-banner"');
    expect(html).not.toContain('data-testid="signal-b-public-provenance"');
    expect(html).not.toContain('data-testid="signal-b-header-provenance"');
  });

  it("does not invent a determination on idle", () => {
    const html = renderToStaticMarkup(createElement(ProvenanceBand, { snapshot: null }));
    expect(html).not.toContain('data-testid="how-this-was-determined"');
    expect(html).toContain('data-testid="command-center-provenance-header"');
    expect(html).not.toContain('data-testid="signal-b-public-provenance"');
  });
});
