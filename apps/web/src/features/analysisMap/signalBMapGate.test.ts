import { describe, expect, it } from "vitest";
import { SIGNAL_B_NEUTRAL_MAP_ENABLED, signalBMapIsEnabled } from "./signalBMapGate";

describe("signal B map gate", () => {
  it("defaults on for the cached selected-time snapshot", () => {
    expect(SIGNAL_B_NEUTRAL_MAP_ENABLED).toBe(true);
    expect(signalBMapIsEnabled()).toBe(true);
  });

  it("still accepts an explicit off override", () => {
    expect(signalBMapIsEnabled(false)).toBe(false);
    expect(SIGNAL_B_NEUTRAL_MAP_ENABLED).toBe(true);
  });
});
