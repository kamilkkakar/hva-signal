import { describe, expect, it } from "vitest";
import { projectLevel2 } from "./level2";
import {
  NATIONAL_AGGREGATION_SPEC,
  PHOENIX_AGGREGATION_SPEC,
  type PublicSignalProvenance,
} from "./types";

const SHA = "ab".repeat(32);

const historical: PublicSignalProvenance = {
  signal_kind: "historical_normalized",
  source: "replay",
  data_status: "replay",
  geometry_version: "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f",
  geometry_sha256: SHA,
  aggregation_spec_version: PHOENIX_AGGREGATION_SPEC,
  reference_source: "cached_reference",
  reference_version: "PHX_ZTSI_REF_V1__HOUR_0300_LOCAL",
  request_fingerprint: "cd".repeat(32),
};

const selectedTime: PublicSignalProvenance = {
  signal_kind: "selected_time_snapshot",
  source: "fortyguard_cached",
  data_status: "cached",
  geometry_version:
    "US_CENSUS_TIGERLINE.census_tract.2025.PLACE_1714000.NATIONAL_PLACE_GEOGRAPHY_V1.aaaaaaaa",
  geometry_sha256: SHA,
  aggregation_spec_version: NATIONAL_AGGREGATION_SPEC,
  request_fingerprint: "ef".repeat(32),
};

describe("Level 2 disclosure", () => {
  it("puts versions and hashes behind disclosure rows for A", () => {
    const rows = projectLevel2(historical, {
      area_config_sha256: "11".repeat(32),
      reference_source_sha256: "22".repeat(32),
    });
    const keys = rows.map((row) => row.key);
    expect(keys).toContain("geometry_version");
    expect(keys).toContain("aggregation_spec_version");
    expect(keys).toContain("reference_version");
    expect(keys).toContain("geometry_sha256");
    expect(keys).toContain("request_fingerprint");
    expect(rows.find((row) => row.key === "geometry_sha256")?.kind).toBe("hash");
  });

  it("omits every reference row on B", () => {
    const rows = projectLevel2(selectedTime, {
      reference_source_sha256: "22".repeat(32),
    });
    expect(rows.map((row) => row.key).join(",")).not.toMatch(/reference/i);
    expect(rows.map((row) => row.label).join(",")).not.toMatch(/reference/i);
    expect(rows.find((row) => row.key === "contract_banner")?.value).toBe("FORTYGUARD CACHED");
  });

  it("rejects B that carries a historical reference", () => {
    expect(() =>
      projectLevel2({
        ...selectedTime,
        reference_version: "PHX_ZTSI_REF_V1",
      }),
    ).toThrow(/historical reference/);
  });
});
