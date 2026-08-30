import { describe, expect, it } from "vitest";
import { MAP_INTERACTION_ENABLED, mapInteractionIsEnabled } from "./flags";

describe("map interaction gate", () => {
  it("defaults off so CommandCenter and MapStage stay the landing path", () => {
    expect(MAP_INTERACTION_ENABLED).toBe(false);
    expect(mapInteractionIsEnabled()).toBe(false);
  });

  it("accepts an explicit stitch override without flipping the default", () => {
    expect(mapInteractionIsEnabled(true)).toBe(true);
    expect(MAP_INTERACTION_ENABLED).toBe(false);
  });
});
