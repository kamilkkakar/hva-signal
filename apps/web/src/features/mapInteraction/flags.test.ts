import { describe, expect, it } from "vitest";
import { MAP_INTERACTION_ENABLED, mapInteractionIsEnabled } from "./flags";

describe("map interaction gate", () => {
  it("defaults on for the I-MAP stitch branch", () => {
    expect(MAP_INTERACTION_ENABLED).toBe(true);
    expect(mapInteractionIsEnabled()).toBe(true);
  });

  it("still accepts an explicit off override", () => {
    expect(mapInteractionIsEnabled(false)).toBe(false);
    expect(MAP_INTERACTION_ENABLED).toBe(true);
  });
});
