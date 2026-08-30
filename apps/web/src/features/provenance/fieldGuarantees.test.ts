import { describe, expect, it } from "vitest";
import { SignalProvenanceError } from "./banner";
import {
  activeSignalKind,
  assertAbFieldGuarantees,
  assertBHasNoReference,
  publicBDump,
  refuseAreasCatalogAsBProvenance,
} from "./fieldGuarantees";
import { selectedTimeLines } from "./lines";
import {
  decision8PanelPermitted,
  legacyThermalSource,
  qaHoverPermitted,
  referenceLinePermitted,
} from "./rail";
import {
  A_REQUIRED_WHEN_COMPUTED,
  B_FORBIDDEN_COPY,
  B_FORBIDDEN_FIELDS,
  B_REQUIRED_WHEN_PATH_KNOWN,
  NATIONAL_AGGREGATION_SPEC,
  PHOENIX_AGGREGATION_SPEC,
  type PublicSignalProvenance,
} from "./types";

const SHA = "ab".repeat(32);
const PHOENIX_GEOM =
  "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f";
const NATIONAL_GEOM =
  "US_CENSUS_TIGERLINE.census_tract.2025.PLACE_1714000.NATIONAL_PLACE_GEOGRAPHY_V1.aaaaaaaa";
const PHOENIX_REF = "PHX_ZTSI_REF_V1__HOUR_0300_LOCAL";

const A_VS_B_FIELD_MATRIX: ReadonlyArray<{
  field: string;
  aComputed: boolean;
  bPathKnown: boolean;
}> = [
  { field: "source", aComputed: true, bPathKnown: true },
  { field: "data_status", aComputed: true, bPathKnown: true },
  { field: "target_timestamp", aComputed: true, bPathKnown: true },
  { field: "timezone", aComputed: true, bPathKnown: true },
  { field: "geometry_version", aComputed: true, bPathKnown: true },
  { field: "geometry_sha256", aComputed: false, bPathKnown: true },
  { field: "aggregation_spec_version", aComputed: true, bPathKnown: true },
  { field: "reference_source", aComputed: true, bPathKnown: false },
  { field: "reference_version", aComputed: true, bPathKnown: false },
];

function historical(overrides: Partial<PublicSignalProvenance> = {}): PublicSignalProvenance {
  return {
    signal_kind: "historical_normalized",
    source: "replay",
    data_status: "replay",
    target_timestamp: "2022-06-30T03:00:00",
    timezone: "America/Phoenix",
    geometry_version: PHOENIX_GEOM,
    aggregation_spec_version: PHOENIX_AGGREGATION_SPEC,
    reference_source: "cached_reference",
    reference_version: PHOENIX_REF,
    request_fingerprint: "cd".repeat(32),
    ...overrides,
  };
}

function selectedTime(overrides: Partial<PublicSignalProvenance> = {}): PublicSignalProvenance {
  return {
    signal_kind: "selected_time_snapshot",
    source: "fortyguard_cached",
    data_status: "cached",
    target_timestamp: "2024-07-15T15:00:00",
    timezone: "America/Chicago",
    geometry_version: NATIONAL_GEOM,
    geometry_sha256: SHA,
    aggregation_spec_version: NATIONAL_AGGREGATION_SPEC,
    request_fingerprint: "ef".repeat(32),
    ...overrides,
  };
}

describe("A vs B field guarantee matrix", () => {
  it.each(A_VS_B_FIELD_MATRIX)(
    "$field required on A=$aComputed B=$bPathKnown",
    ({ field, aComputed, bPathKnown }) => {
      expect(A_REQUIRED_WHEN_COMPUTED.includes(field as never)).toBe(aComputed);
      expect(B_REQUIRED_WHEN_PATH_KNOWN.includes(field as never)).toBe(bPathKnown);
    },
  );

  it("forbids reference and D8 fields on B dumps", () => {
    const dumped = publicBDump(selectedTime());
    expect(dumped).not.toHaveProperty("reference_version");
    expect(dumped).not.toHaveProperty("reference_source");
    for (const field of B_FORBIDDEN_FIELDS) {
      expect(dumped[field] ?? null).toBeNull();
    }
  });

  it("rejects B reference_version", () => {
    expect(() =>
      assertBHasNoReference(selectedTime({ reference_version: PHOENIX_REF })),
    ).toThrow(SignalProvenanceError);
  });

  it("rejects A computed without reference_version", () => {
    expect(() =>
      assertAbFieldGuarantees({
        historical: historical({ reference_version: null }),
        aComputed: true,
      }),
    ).toThrow(/Signal A computed/);
  });

  it("requires geometry_sha256 on path-known B", () => {
    expect(() =>
      assertAbFieldGuarantees({
        selectedTime: selectedTime({ geometry_sha256: null }),
        bPathKnown: true,
      }),
    ).toThrow(/Signal B path-known/);
  });

  it("keeps A and B fingerprints distinct", () => {
    expect(() =>
      assertAbFieldGuarantees({
        historical: historical({ request_fingerprint: "99".repeat(32) }),
        selectedTime: selectedTime({ request_fingerprint: "99".repeat(32) }),
      }),
    ).toThrow(/fingerprints/);
  });

  it("does not map GET /areas reference_version onto B", () => {
    expect(() => refuseAreasCatalogAsBProvenance(PHOENIX_REF)).toThrow(
      /not B provenance/,
    );
  });

  it("rejects national B that inherits Phoenix stamps", () => {
    expect(() =>
      assertAbFieldGuarantees({
        selectedTime: selectedTime({ geometry_version: PHOENIX_GEOM }),
        nationalAreaId: "us-place-1714000-2025-national-place-geography-v1",
      }),
    ).toThrow(/Phoenix/);
    expect(() =>
      assertAbFieldGuarantees({
        selectedTime: selectedTime({
          aggregation_spec_version: PHOENIX_AGGREGATION_SPEC,
        }),
        nationalAreaId: "us-place-1714000-2025-national-place-geography-v1",
      }),
    ).toThrow(/Phoenix aggregation/);
  });

  it("selects the active signal without blending fields", () => {
    const active = activeSignalKind(
      "selected_time_snapshot",
      historical(),
      selectedTime(),
    );
    expect(active?.signal_kind).toBe("selected_time_snapshot");
    expect(active?.reference_version).toBeUndefined();
  });
});

describe("B rail locks", () => {
  it("hides Decision 8, q_A hover, and Reference on B", () => {
    expect(decision8PanelPermitted("selected_time_snapshot")).toBe(false);
    expect(qaHoverPermitted("selected_time_snapshot")).toBe(false);
    expect(referenceLinePermitted("selected_time_snapshot")).toBe(false);
    expect(decision8PanelPermitted("historical_normalized")).toBe(true);
  });

  it("nulls legacy_thermal_source when B is requested", () => {
    expect(
      legacyThermalSource({
        selectedTimeRequested: true,
        historicalSource: "replay",
      }),
    ).toBeNull();
    expect(
      legacyThermalSource({
        selectedTimeRequested: false,
        historicalSource: "replay",
      }),
    ).toBe("replay");
  });

  it("omits Reference / D8 / q_A copy from B lines", () => {
    const text = selectedTimeLines(selectedTime()).join("\n");
    for (const token of B_FORBIDDEN_COPY) {
      expect(text).not.toContain(token);
    }
    expect(text).toContain("Selected-Time Thermal Snapshot");
    expect(text).toContain("Target source: FORTYGUARD CACHED");
    expect(text).toContain("Aggregation:");
  });
});
