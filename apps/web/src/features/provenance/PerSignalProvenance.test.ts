import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { PerSignalProvenance } from "./PerSignalProvenance";
import {
  NATIONAL_AGGREGATION_SPEC,
  PHOENIX_AGGREGATION_SPEC,
  type PublicSignalProvenance,
} from "./types";

const historical: PublicSignalProvenance = {
  signal_kind: "historical_normalized",
  source: "replay",
  data_status: "replay",
  target_timestamp: "2022-06-30T03:00:00",
  timezone: "America/Phoenix",
  geometry_version:
    "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f",
  aggregation_spec_version: PHOENIX_AGGREGATION_SPEC,
  reference_source: "cached_reference",
  reference_version: "PHX_ZTSI_REF_V1",
};

const selectedTime: PublicSignalProvenance = {
  signal_kind: "selected_time_snapshot",
  source: "fortyguard_cached",
  data_status: "cached",
  target_timestamp: "2024-07-15T15:00:00",
  timezone: "America/Chicago",
  geometry_version:
    "US_CENSUS_TIGERLINE.census_tract.2025.PLACE_1714000.NATIONAL_PLACE_GEOGRAPHY_V1.aaaaaaaa",
  geometry_sha256: "ab".repeat(32),
  aggregation_spec_version: NATIONAL_AGGREGATION_SPEC,
};

describe("PerSignalProvenance", () => {
  it("renders two rails and never a collapsed SourceTape", () => {
    const html = renderToStaticMarkup(
      createElement(PerSignalProvenance, {
        historical,
        selectedTime,
        selectedTimeRequested: true,
      }),
    );
    expect(html).toContain("data-testid=\"per-signal-provenance\"");
    expect(html).toContain("data-collapsed=\"false\"");
    expect(html).toContain("data-testid=\"signal-a-provenance\"");
    expect(html).toContain("data-testid=\"signal-b-provenance\"");
    expect(html).not.toContain("source-tape");
    expect(html).not.toContain("Thermal source:");
  });

  it("keeps Decision 8 / Reference off the B rail", () => {
    const html = renderToStaticMarkup(
      createElement(PerSignalProvenance, {
        historical,
        selectedTime,
        active: "selected_time_snapshot",
        selectedTimeRequested: true,
      }),
    );
    expect(html).toContain("data-testid=\"signal-b-provenance\"");
    expect(html).not.toContain("data-testid=\"signal-a-provenance\"");
    expect(html).toContain("data-decision8=\"false\"");
    expect(html).toContain("data-reference=\"false\"");
    expect(html).not.toContain("decision8-reference-version");
    expect(html).not.toContain("Reference:");
    expect(html).not.toContain("PHX_ZTSI_REF_V1");
    expect(html).toContain("Selected-Time Thermal Snapshot");
    expect(html).toContain("FORTYGUARD CACHED");
  });

  it("shows Reference and Decision 8 only on the A rail", () => {
    const html = renderToStaticMarkup(
      createElement(PerSignalProvenance, {
        historical,
        selectedTime,
        active: "historical_normalized",
      }),
    );
    expect(html).toContain("data-decision8=\"true\"");
    expect(html).toContain("decision8-reference-version");
    expect(html).toContain("Reference:");
    expect(html).not.toContain("data-testid=\"signal-b-provenance\"");
  });

  it("clears legacy thermal source when B is requested", () => {
    const html = renderToStaticMarkup(
      createElement(PerSignalProvenance, {
        historical,
        selectedTime,
        selectedTimeRequested: true,
      }),
    );
    expect(html).toContain("data-legacy-thermal-source=\"\"");
  });
});
