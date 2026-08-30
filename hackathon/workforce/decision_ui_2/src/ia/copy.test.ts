import { describe, expect, it } from "vitest";
import * as copy from "./copy";
import { assertNoForbidden, collectPublishedCopy } from "@/test/forbidden";

describe("public copy", () => {
  it("does not publish forbidden technical or overclaim tokens", () => {
    const published = collectPublishedCopy(
      Object.entries(copy)
        .filter(([key]) => key !== "FORBIDDEN_PUBLIC")
        .map(([, value]) => value),
    );
    expect(() => assertNoForbidden(published)).not.toThrow();
    expect(published).toContain("analysis area");
    expect(published.toLowerCase()).not.toContain("current conditions");
  });

  it("explains analysis areas once and keeps GEOID secondary", () => {
    expect(copy.AREA_EXPLAIN_ONCE).toContain("25 consistent analysis areas");
    expect(copy.GEOID_SECONDARY).toContain("secondary identifier");
  });
});
