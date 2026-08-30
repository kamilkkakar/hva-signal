import { describe, expect, it } from "vitest";
import { selectedZoneLevel1 } from "./selectedZone";

describe("selected-zone Level 1", () => {
  it("carries zone coverage without hashes", () => {
    const view = selectedZoneLevel1({
      zoneId: "04013114100",
      coverage: "valid",
      observation: "2022-06-30 · 03:00 local",
      source: "Replay fixture",
      signalKind: "historical_normalized",
    });
    expect(view.coverage).toBe("valid");
    expect(JSON.stringify(view)).not.toMatch(/[0-9a-f]{64}/i);
  });

  it("rejects a SHA wall on the zone line", () => {
    expect(() =>
      selectedZoneLevel1({
        zoneId: "ab".repeat(32),
        coverage: "missing",
        observation: "Selected hour",
        source: "Cached vendor target",
        signalKind: "selected_time_snapshot",
      }),
    ).toThrow(/must not expose SHA/);
  });
});
