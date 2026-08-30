import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { PublicProvenanceExperience } from "./PublicProvenanceExperience";
import {
  NATIONAL_AGGREGATION_SPEC,
  PHOENIX_AGGREGATION_SPEC,
  type PublicSignalProvenance,
} from "./types";

const SHA = "ab".repeat(32);
const PHOENIX_GEOM =
  "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f";

const historical: PublicSignalProvenance = {
  signal_kind: "historical_normalized",
  source: "replay",
  data_status: "replay",
  target_timestamp: "2022-06-30T03:00:00",
  timezone: "America/Phoenix",
  geometry_version: PHOENIX_GEOM,
  geometry_sha256: SHA,
  aggregation_spec_version: PHOENIX_AGGREGATION_SPEC,
  reference_source: "cached_reference",
  reference_version: "PHX_ZTSI_REF_V1__HOUR_0300_LOCAL",
};

const selectedTime: PublicSignalProvenance = {
  signal_kind: "selected_time_snapshot",
  source: "fortyguard_cached",
  data_status: "cached",
  target_timestamp: "2024-07-15T15:00:00",
  timezone: "America/Chicago",
  geometry_version:
    "US_CENSUS_TIGERLINE.census_tract.2025.PLACE_1714000.NATIONAL_PLACE_GEOGRAPHY_V1.aaaaaaaa",
  geometry_sha256: SHA,
  aggregation_spec_version: NATIONAL_AGGREGATION_SPEC,
};

function level1Html(html: string, testId: string): string {
  const match = html.match(
    new RegExp(`data-testid="${testId}-level1"[^>]*>([\\s\\S]*?)</dl>`),
  );
  return match?.[1] ?? "";
}

describe("PublicProvenanceExperience", () => {
  it("renders independent A/B Level 1 rails and never a SourceTape", () => {
    const html = renderToStaticMarkup(
      createElement(PublicProvenanceExperience, {
        historical,
        selectedTime,
        selectedTimeRequested: true,
        historicalCoverage: { valid: 25, expected: 25 },
        selectedTimeCoverage: { valid: 23, expected: 25 },
        historicalAreaId: "phoenix-demo",
      }),
    );
    expect(html).toContain('data-testid="public-provenance-experience"');
    expect(html).toContain('data-collapsed="false"');
    expect(html).toContain('data-testid="signal-a-public-provenance"');
    expect(html).toContain('data-testid="signal-b-public-provenance"');
    expect(html).not.toContain("source-tape");
    expect(html).not.toContain("Thermal source:");
    expect(html).toContain("Replay fixture");
    expect(html).toContain("Cached vendor target");
    expect(html).toContain("25 / 25");
    expect(html).toContain("23 / 25");
    expect(html).toContain("REPLAY");
    expect(html).toContain("CACHED");
    expect(html).not.toContain("FORTYGUARD LIVE");
  });

  it("keeps hashes out of Level 1 and inside Level 2 details", () => {
    const html = renderToStaticMarkup(
      createElement(PublicProvenanceExperience, {
        historical,
        historicalCoverage: { valid: 25, expected: 25 },
        historicalAreaId: "phoenix-demo",
        historicalLevel2Extras: { area_config_sha256: SHA },
      }),
    );
    const level1 = level1Html(html, "signal-a-public-provenance");
    expect(level1).toContain("Source");
    expect(level1).toContain("Observation");
    expect(level1).toContain("Analysis geography");
    expect(level1).toContain("Coverage");
    expect(level1).toContain("Evidence mode");
    expect(level1).not.toContain(SHA);
    expect(level1).not.toContain(PHOENIX_GEOM);
    expect(level1).not.toContain("PHX_ZTSI_REF");
    expect(html).toContain('data-testid="signal-a-public-provenance-level2"');
    expect(html).toContain("Method and versions");
    expect(html).toContain(SHA);
    expect(html).toContain(PHOENIX_GEOM);
  });

  it("keeps Reference off the B rail", () => {
    const html = renderToStaticMarkup(
      createElement(PublicProvenanceExperience, {
        historical,
        selectedTime,
        active: "selected_time_snapshot",
        selectedTimeRequested: true,
      }),
    );
    expect(html).toContain('data-testid="signal-b-public-provenance"');
    expect(html).not.toContain('data-testid="signal-a-public-provenance"');
    expect(html).toContain('data-reference="false"');
    expect(html).not.toContain("Historical reference");
    expect(html).not.toContain("PHX_ZTSI_REF");
    expect(html).not.toContain("NOW");
  });

  it("clears legacy thermal source when B is requested", () => {
    const html = renderToStaticMarkup(
      createElement(PublicProvenanceExperience, {
        historical,
        selectedTime,
        selectedTimeRequested: true,
      }),
    );
    expect(html).toContain('data-legacy-thermal-source=""');
  });
});
