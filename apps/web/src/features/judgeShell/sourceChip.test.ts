import { describe, expect, it } from "vitest";
import { contextSourceChip, publicSourceChip } from "./sourceChip";

describe("public source chips", () => {
  it("never surfaces a vendor name", () => {
    expect(publicSourceChip("FORTYGUARD LIVE")).toBe("LIVE");
    expect(publicSourceChip("FORTYGUARD CACHED")).toBe("CACHED");
    expect(publicSourceChip("REPLAY")).toBe("REPLAY");
    for (const banner of [
      "FORTYGUARD LIVE",
      "FORTYGUARD CACHED",
      "REPLAY",
      "PARTIAL",
      "UNAVAILABLE",
    ] as const) {
      expect(publicSourceChip(banner)).not.toMatch(/fortyguard/i);
    }
  });

  it("shows replay before a job exists", () => {
    expect(contextSourceChip("UNAVAILABLE", false)).toBe("REPLAY");
    expect(contextSourceChip("REPLAY", true)).toBe("REPLAY");
  });
});
