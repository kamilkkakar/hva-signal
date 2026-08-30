import { describe, expect, it } from "vitest";
import { SignalProvenanceError } from "./banner";
import {
  assertLevel1HasNoShaWall,
  formatCoverage,
  geographyLine,
  observationLine,
  projectLevel1,
  type PublicLevel1,
} from "./level1";
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

describe("Level 1 public provenance", () => {
  it("projects source, time, geography, coverage, and evidence mode", () => {
    const view = projectLevel1({
      view: historical,
      coverage: { valid: 25, expected: 25 },
      areaId: "phoenix-demo",
    });
    expect(view).toMatchObject({
      title: "Nighttime Historical Thermal Signal",
      source: "Replay fixture",
      observation: "2022-06-30 · 03:00 local · America/Phoenix",
      geography: "25-zone Phoenix demo AOI",
      coverage: "25 / 25",
      evidenceMode: "REPLAY",
    });
  });

  it("keeps cached B as CACHED and never LIVE", () => {
    const view = projectLevel1({
      view: selectedTime,
      coverage: { valid: 23, expected: 25 },
      areaId: "us-place-1714000-2025-national-place-geography-v1",
    });
    expect(view.source).toBe("Cached vendor target");
    expect(view.evidenceMode).toBe("CACHED");
    expect(view.geography).toBe("25-zone analysis window");
    expect(view.observation).toBe("2024-07-15 · 15:00 · America/Chicago");
    expect(view.coverage).toBe("23 / 25");
    expect(view.observation).not.toMatch(/NOW|current/i);
  });

  it("refuses illegal live-beats-cached pairing", () => {
    expect(() =>
      projectLevel1({
        view: { ...selectedTime, data_status: "live" },
      }),
    ).toThrow(/live does not beat cached/);
  });

  it("does not put SHA or protocol stamps on Level 1", () => {
    const view = projectLevel1({
      view: historical,
      coverage: { valid: 25, expected: 25 },
      areaId: "phoenix-demo",
    });
    const blob = Object.values(view).join(" ");
    expect(blob).not.toMatch(/[0-9a-f]{64}/i);
    expect(blob).not.toContain(PHOENIX_GEOM);
    expect(blob).not.toContain("PHX_ZTSI_REF");
    expect(blob).not.toContain("sha256");
  });

  it("throws if a Level 1 field is a SHA wall", () => {
    const wall: PublicLevel1 = {
      signalKind: "historical_normalized",
      title: "Nighttime Historical Thermal Signal",
      source: "Replay fixture",
      observation: "03:00 local",
      geography: PHOENIX_GEOM,
      coverage: "25 / 25",
      evidenceMode: "REPLAY",
    };
    expect(() => assertLevel1HasNoShaWall(wall)).toThrow(SignalProvenanceError);
  });

  it("uses 03:00 local for A even without a timestamp", () => {
    expect(
      observationLine({
        signal_kind: "historical_normalized",
      }),
    ).toBe("03:00 local");
  });

  it("labels national geography as an analysis window", () => {
    expect(geographyLine(selectedTime, "us-place-1714000-2025-national-place-geography-v1")).toBe(
      "25-zone analysis window",
    );
    expect(geographyLine(historical, "phoenix-demo")).not.toMatch(/city/i);
  });

  it("formats unknown coverage without inventing 25 / 25", () => {
    expect(formatCoverage(null)).toBe("unknown");
    expect(
      projectLevel1({ view: historical, areaId: "phoenix-demo" }).coverage,
    ).toBe("unknown");
  });
});
