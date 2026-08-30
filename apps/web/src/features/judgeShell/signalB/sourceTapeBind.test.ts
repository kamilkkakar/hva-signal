import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { refuseCollapsedSourceTape } from "@/features/provenance/banner";
import {
  NATIONAL_AGGREGATION_SPEC,
  PHOENIX_AGGREGATION_SPEC,
  type PublicSignalProvenance,
} from "@/features/provenance/types";
import {
  CommandCenterProvenance,
  commandCenterProvenanceMode,
  P1_LANDING_SELECTED_TIME_REQUESTED,
  refuseCollapsedCommandCenterTape,
} from "./sourceTapeBind";

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
  timezone: "America/Phoenix",
  geometry_version:
    "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f",
  geometry_sha256: "ab".repeat(32),
  aggregation_spec_version: PHOENIX_AGGREGATION_SPEC,
};

describe("CommandCenterProvenance Q7 bind", () => {
  it("keeps the P1 landing on a single A-only SourceTape", () => {
    expect(P1_LANDING_SELECTED_TIME_REQUESTED).toBe(false);
    expect(commandCenterProvenanceMode(false)).toBe("a-only-tape");
    const html = renderToStaticMarkup(
      createElement(CommandCenterProvenance, {
        selectedTimeRequested: false,
        aOnlyBanner: "REPLAY",
        historical,
        selectedTime,
      }),
    );
    expect(html).toContain('data-testid="source-banner"');
    expect(html).toContain("REPLAY");
    expect(html).not.toContain('data-testid="per-signal-provenance"');
  });

  it("uses independent rails when Signal B is requested", () => {
    expect(commandCenterProvenanceMode(true)).toBe("per-signal");
    const html = renderToStaticMarkup(
      createElement(CommandCenterProvenance, {
        selectedTimeRequested: true,
        aOnlyBanner: "REPLAY",
        historical,
        selectedTime,
      }),
    );
    expect(html).toContain('data-testid="per-signal-provenance"');
    expect(html).toContain('data-testid="signal-a-provenance"');
    expect(html).toContain('data-testid="signal-b-provenance"');
    expect(html).toContain("FORTYGUARD CACHED");
    expect(html).toContain('data-reference="false"');
    expect(html).not.toContain('data-testid="source-banner"');
  });

  it("refuses a collapsed A/B SourceTape", () => {
    expect(() => refuseCollapsedSourceTape()).toThrow(/never collapse/);
    expect(() => refuseCollapsedCommandCenterTape()).toThrow(/never collapse/);
  });

  it("does not treat national aggregation as a B snapshot", () => {
    expect(NATIONAL_AGGREGATION_SPEC).not.toBe(PHOENIX_AGGREGATION_SPEC);
    expect(selectedTime.aggregation_spec_version).toBe(PHOENIX_AGGREGATION_SPEC);
    expect(selectedTime).not.toHaveProperty("reference_version");
    expect(selectedTime).not.toHaveProperty("reference_source");
  });
});
