import { describe, expect, it } from "vitest";
import {
  parseCityCatalog,
  parseWorkspaceCatalog,
  supportedObservationMode,
  supportsSelectedTimeLive,
} from "./cityCatalog";

function serverCity(overrides: Record<string, unknown> = {}) {
  return {
    city_id: "phoenix",
    display_name: "Phoenix",
    state: "AZ",
    timezone: "America/Phoenix",
    local_geography_version: "PHX_DEMO_AOI_POLICY_V1",
    capabilities: {
      local_story: "AVAILABLE",
      type1_live: "READY_FOR_ACQUISITION",
    },
    ...overrides,
  };
}

function evidence(state = "VERIFIED") {
  return {
    state,
    reason: "A reviewed server artifact exists.",
    affected_scope: "local_story",
    next_check: "Repeat integrity checks after a source change.",
  };
}

function validationJurisdiction(overrides: Record<string, unknown> = {}) {
  return {
    jurisdiction_id: "yuma_az",
    display_name: "Yuma",
    region_code: "AZ",
    validation_class: "SMALL_PLACE",
    selectable: false,
    state: "NOT_YET_TESTED",
    reason: "Native small-place evidence has not been validated.",
    affected_scope: ["place_geometry"],
    next_check: "Test every native tract without a minimum count.",
    capabilities: { place_geometry: { ...evidence("NOT_YET_TESTED"), affected_scope: "place_geometry" } },
    ...overrides,
  };
}

describe("server-driven city catalog", () => {
  it("represents a new jurisdiction without a frontend enum edit", () => {
    const [anchorage] = parseCityCatalog({
      cities: [serverCity({
        city_id: "anchorage",
        display_name: "Anchorage",
        state: "AK",
        timezone: "America/Anchorage",
        local_geography_version: null,
        capabilities: {
          local_story: "PARTIAL",
          type1_live: "UNAVAILABLE",
        },
      })],
    });

    expect(anchorage.id).toBe("anchorage-ak");
    expect(anchorage.apiCityId).toBe("anchorage");
    expect(anchorage.hasLocalAnalysis).toBe(false);
    expect(supportsSelectedTimeLive(anchorage)).toBe(false);
    expect(supportedObservationMode(anchorage, "live")).toBe("published");
  });

  it("preserves explicit server capability states", () => {
    const [phoenix] = parseCityCatalog({ cities: [serverCity()] });
    expect(phoenix.capabilities.local_story).toBe("AVAILABLE");
    expect(supportsSelectedTimeLive(phoenix)).toBe(true);
  });

  it("keeps structured validation evidence outside the operational selector", () => {
    const catalog = parseWorkspaceCatalog({
      cities: [serverCity({
        capability_evidence: {
          local_story: evidence(),
          type1_live: { ...evidence("NOT_YET_TESTED"), affected_scope: "type1_live" },
        },
      })],
      validation_jurisdictions: [validationJurisdiction()],
    });

    expect(catalog.cities.map((city) => city.apiCityId)).toEqual(["phoenix"]);
    expect(catalog.cities[0].capabilityEvidence?.type1_live.state).toBe("NOT_YET_TESTED");
    expect(catalog.validationJurisdictions[0].jurisdictionId).toBe("yuma_az");
    expect(catalog.validationJurisdictions[0].selectable).toBe(false);
  });

  it.each([
    validationJurisdiction({ selectable: true }),
    validationJurisdiction({ state: "READY" }),
    validationJurisdiction({ jurisdiction_id: "phoenix" }),
  ])("rejects selectable, invalid, or overlapping validation profiles", (profile) => {
    expect(() => parseWorkspaceCatalog({
      cities: [serverCity()],
      validation_jurisdictions: [profile],
    })).toThrow();
  });

  it("rejects capability evidence that diverges from the city contract", () => {
    expect(() => parseCityCatalog({
      cities: [serverCity({ capability_evidence: { local_story: evidence() } })],
    })).toThrow("does not match");
  });

  it.each([
    { cities: [] },
    { cities: [serverCity({ timezone: "UTC" })] },
    { cities: [serverCity({ capabilities: { type1_live: "READY" } })] },
    { cities: [serverCity(), serverCity()] },
  ])("rejects malformed or ambiguous catalogs", (payload) => {
    expect(() => parseCityCatalog(payload)).toThrow();
  });
});
