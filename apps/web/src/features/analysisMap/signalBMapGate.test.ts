import { describe, expect, it } from "vitest";
import { SIGNAL_B_NEUTRAL_MAP_ENABLED, signalBMapIsEnabled } from "./signalBMapGate";

describe("signal B map gate", () => {
  it("defaults off so the production Phoenix A map stays the landing map", () => {
    expect(SIGNAL_B_NEUTRAL_MAP_ENABLED).toBe(false);
    expect(signalBMapIsEnabled()).toBe(false);
  });

  it("accepts an explicit stitch override without flipping the default", () => {
    expect(signalBMapIsEnabled(true)).toBe(true);
    expect(SIGNAL_B_NEUTRAL_MAP_ENABLED).toBe(false);
  });
});
