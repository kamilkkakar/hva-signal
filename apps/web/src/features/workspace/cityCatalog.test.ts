import { describe, expect, it } from "vitest";
import {
  parseCityCatalog,
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

  it.each([
    { cities: [] },
    { cities: [serverCity({ timezone: "UTC" })] },
    { cities: [serverCity({ capabilities: { type1_live: "READY" } })] },
    { cities: [serverCity(), serverCity()] },
  ])("rejects malformed or ambiguous catalogs", (payload) => {
    expect(() => parseCityCatalog(payload)).toThrow();
  });
});
