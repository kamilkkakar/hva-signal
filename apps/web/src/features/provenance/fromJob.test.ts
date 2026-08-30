import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { bindProvenanceFromJob, coverageFromZones, selectedTimeFromSection } from "./fromJob";
import { projectLevel1 } from "./level1";
import { PHOENIX_AGGREGATION_SPEC, type PublicSignalProvenance } from "./types";

const here = dirname(fileURLToPath(import.meta.url));

const historical: PublicSignalProvenance = {
  signal_kind: "historical_normalized",
  source: "replay",
  data_status: "replay",
  target_timestamp: "2022-06-30T03:00:00",
  timezone: "America/Phoenix",
  geometry_version: "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f",
  aggregation_spec_version: PHOENIX_AGGREGATION_SPEC,
  reference_source: "cached_reference",
  reference_version: "PHX_ZTSI_REF_V1",
};

describe("Q7 bind adapter (provenance feature, not CommandCenterShell)", () => {
  it("does not import sourceBannerLabel", () => {
    const source = readFileSync(join(here, "fromJob.ts"), "utf8");
    expect(source).not.toContain("sourceBanner");
    expect(source).not.toContain("sourceBannerLabel");
    expect(source).not.toMatch(/request\.data_mode/);
  });

  it("maps a phoenix-demo A-only replay job without collapsing B", () => {
    const bound = bindProvenanceFromJob({
      job: {
        status: "complete",
        request: {
          area_id: "phoenix-demo",
          analysis_time: "2022-06-30T12:00:00",
          data_mode: "replay",
        },
        result: {
          data_status: "replay",
          zones: Array.from({ length: 25 }, (_, index) => ({
            zone_id: String(index),
            thermal_observation_valid: true,
          })),
          versions: {
            zone_geometry_version:
              "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f",
            thermal_aggregation_version: PHOENIX_AGGREGATION_SPEC,
          },
          hazard_spread: {
            reference_version: "PHX_ZTSI_REF_V1__HOUR_0300_LOCAL",
            zone_geometry_version:
              "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f",
          },
          area_config_sha256: "aa".repeat(32),
        },
      },
    });
    expect(bound.collapsed).toBe(false);
    expect(bound.selectedTimeRequested).toBe(false);
    expect(bound.selectedTime).toBeNull();
    expect(bound.legacyThermalSource).toBe("replay");
    expect(bound.historical?.source).toBe("replay");
    expect(bound.historical?.data_status).toBe("replay");
    expect(bound.historical?.target_timestamp).toBe("2022-06-30T03:00:00");
    expect(bound.historical?.timezone).toBe("America/Phoenix");
    expect(bound.historicalCoverage).toEqual({ valid: 25, expected: 25 });
    const level1 = projectLevel1({
      view: bound.historical!,
      coverage: bound.historicalCoverage,
      areaId: bound.historicalAreaId,
    });
    expect(level1.evidenceMode).toBe("REPLAY");
    expect(level1.coverage).toBe("25 / 25");
    expect(level1.geography).toBe("25-zone Phoenix demo AOI");
  });

  it("ignores request data_mode when the served path is cached", () => {
    const bound = bindProvenanceFromJob({
      selectedTimeRequested: true,
      historical,
      selectedTime: {
        signal_kind: "selected_time_snapshot",
        source: "fortyguard_cached",
        data_status: "cached",
        target_timestamp: "2024-07-15T15:00:00",
        timezone: "America/Phoenix",
        geometry_version: "geom-b",
        geometry_sha256: "ab".repeat(32),
        aggregation_spec_version: "HVA_NATIONAL_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
        request_fingerprint: "11".repeat(32),
      },
      job: {
        request: { area_id: "phoenix-demo", data_mode: "replay" },
        result: { data_status: "live", thermal_source: "fortyguard_live" },
      },
    });
    expect(bound.legacyThermalSource).toBeNull();
    expect(bound.selectedTime?.source).toBe("fortyguard_cached");
    expect(bound.selectedTime?.data_status).toBe("cached");
    expect(
      projectLevel1({ view: bound.selectedTime! }).evidenceMode,
    ).toBe("CACHED");
  });

  it("throws when cached source is paired with live status", () => {
    expect(() =>
      bindProvenanceFromJob({
        job: {
          request: { area_id: "phoenix-demo", analysis_time: "2022-06-30" },
          result: {
            data_status: "live",
            thermal_source: "fortyguard_cached",
          },
        },
      }),
    ).toThrow(/live does not beat cached/);
  });

  it("rejects B reference on the section adapter", () => {
    expect(() =>
      selectedTimeFromSection({
        requested: true,
        provenance_source: "replay",
        data_status: "replay",
        reference_version: "PHX_ZTSI_REF_V1",
      }),
    ).toThrow(/historical reference/);
  });

  it("emits an unavailable B rail when B is requested without a snapshot", () => {
    const bound = bindProvenanceFromJob({
      historical,
      selectedTimeRequested: true,
    });
    expect(bound.selectedTime?.signal_kind).toBe("selected_time_snapshot");
    expect(bound.selectedTime?.data_status).toBe("unavailable");
    expect(bound.selectedTime?.reference_version).toBeUndefined();
    expect(bound.legacyThermalSource).toBeNull();
  });

  it("counts valid vs missing zones without inventing coverage", () => {
    expect(
      coverageFromZones([
        { coverage_status: "valid" },
        { coverage_status: "missing" },
        { thermal_observation_valid: true },
      ]),
    ).toEqual({ valid: 2, expected: 25 });
    expect(coverageFromZones(null)).toBeNull();
  });
});
