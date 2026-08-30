import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { refuseCollapsedSourceTape } from "./banner";
import {
  CommandCenterProvenance,
  CommandCenterProvenanceHeader,
  commandCenterProvenanceMode,
  P1_LANDING_SELECTED_TIME_REQUESTED,
  refuseCollapsedCommandCenterTape,
} from "./sourceTapeBind";
import {
  NATIONAL_AGGREGATION_SPEC,
  PHOENIX_AGGREGATION_SPEC,
  type PublicSignalProvenance,
} from "./types";

const here = dirname(fileURLToPath(import.meta.url));

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

describe("CommandCenterProvenanceHeader Q7 bind", () => {
  it("does not import the live-wins mapper or header tape", () => {
    const source = readFileSync(join(here, "sourceTapeBind.tsx"), "utf8");
    const imports = source
      .split("\n")
      .filter((line) => line.startsWith("import "))
      .join("\n");
    expect(imports).not.toContain("sourceBanner");
    expect(imports).not.toContain("@/utils/");
    expect(imports).not.toContain("command-center");
  });

  it("keeps the P1 landing on a single A-only Level 1 rail", () => {
    expect(P1_LANDING_SELECTED_TIME_REQUESTED).toBe(false);
    expect(commandCenterProvenanceMode(false)).toBe("a-only-level1");
    const html = renderToStaticMarkup(
      createElement(CommandCenterProvenanceHeader, {
        job: {
          status: "complete",
          request: {
            area_id: "phoenix-demo",
            analysis_time: "2022-06-30T12:00:00",
            data_mode: "replay",
          },
          result: {
            data_status: "replay",
            versions: {
              zone_geometry_version:
                "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f",
              thermal_aggregation_version: PHOENIX_AGGREGATION_SPEC,
            },
            hazard_spread: { reference_version: "PHX_ZTSI_REF_V1" },
          },
        },
      }),
    );
    expect(html).toContain('data-testid="command-center-provenance-header"');
    expect(html).toContain('data-mode="a-only-level1"');
    expect(html).toContain('data-collapsed="false"');
    expect(html).toContain('data-testid="signal-a-header-provenance"');
    expect(html).toContain("Replay fixture");
    expect(html).toContain("REPLAY");
    expect(html).not.toContain("source-tape");
    expect(html).not.toContain("Thermal source:");
    expect(html).not.toContain("data-testid=\"source-banner\"");
    expect(html).not.toContain("data-testid=\"signal-b-header-provenance\"");
  });

  it("uses independent rails when Signal B is requested", () => {
    expect(commandCenterProvenanceMode(true)).toBe("per-signal");
    const html = renderToStaticMarkup(
      createElement(CommandCenterProvenance, {
        historical,
        selectedTime,
        selectedTimeRequested: true,
      }),
    );
    expect(html).toContain('data-mode="per-signal"');
    expect(html).toContain('data-testid="signal-a-header-provenance"');
    expect(html).toContain('data-testid="signal-b-header-provenance"');
    expect(html).toContain("Cached vendor target");
    expect(html).toContain("CACHED");
    expect(html).toContain('data-reference="false"');
    expect(html).toContain('data-legacy-thermal-source=""');
    expect(html).not.toContain("FORTYGUARD LIVE");
    expect(html).not.toContain("source-tape");
    expect(html).not.toContain("data-testid=\"source-banner\"");
  });

  it("keeps cached B as CACHED when request data_mode is replay", () => {
    const html = renderToStaticMarkup(
      createElement(CommandCenterProvenanceHeader, {
        selectedTimeRequested: true,
        historical,
        selectedTime,
        job: {
          request: { area_id: "phoenix-demo", data_mode: "replay" },
          result: { data_status: "live", thermal_source: "fortyguard_live" },
        },
      }),
    );
    const b = html.match(
      /data-testid="signal-b-header-provenance"[\s\S]*?<\/article>/,
    )?.[0];
    expect(b).toContain("CACHED");
    expect(b).not.toContain("LIVE");
    expect(b).not.toContain("REPLAY");
  });

  it("throws instead of labeling live-wins on an illegal pair", () => {
    expect(() =>
      renderToStaticMarkup(
        createElement(CommandCenterProvenanceHeader, {
          job: {
            request: { area_id: "phoenix-demo", analysis_time: "2022-06-30" },
            result: {
              data_status: "live",
              thermal_source: "fortyguard_cached",
            },
          },
        }),
      ),
    ).toThrow(/live does not beat cached/);
  });

  it("idles without a five-cell LIVE/CACHED tape", () => {
    const html = renderToStaticMarkup(createElement(CommandCenterProvenanceHeader, {}));
    expect(html).toContain('data-evidence-mode="UNAVAILABLE"');
    expect(html).toContain("UNAVAILABLE");
    expect(html).not.toContain("source-tape");
    expect(html).not.toContain("data-segment=\"live\"");
    expect(html).not.toContain("data-segment=\"cached\"");
  });

  it("refuses a collapsed A/B SourceTape", () => {
    expect(() => refuseCollapsedSourceTape()).toThrow(/never collapse/);
    expect(() => refuseCollapsedCommandCenterTape()).toThrow(/never collapse/);
  });
});
