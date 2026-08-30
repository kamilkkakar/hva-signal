import { describe, expect, it } from "vitest";
import {
  FORBIDDEN_STORY_CHROME,
  INSUFFICIENT_DOES_NOT,
  INSUFFICIENT_HEADLINE,
  INSUFFICIENT_SUPPORTS,
  SUFFICIENT_DOES_NOT,
  SUFFICIENT_HEADLINE,
  SUFFICIENT_SUPPORTS,
  publishedStoryCopy,
} from "./copy";

describe("result story copy lock", () => {
  it("keeps sufficient as comparison, not harm or intervention", () => {
    expect(SUFFICIENT_HEADLINE).toBe("Spatial differences are clear enough to compare");
    expect(SUFFICIENT_SUPPORTS).toContain("one input");
    expect(SUFFICIENT_DOES_NOT).toContain("Not a probability of harm");
    expect(SUFFICIENT_DOES_NOT).toContain("Not a severity classification");
    expect(SUFFICIENT_DOES_NOT).toContain("Not a validated intervention recommendation");
  });

  it("keeps insufficient unranked, not an all-clear", () => {
    expect(INSUFFICIENT_HEADLINE).toContain("too similar to rank defensibly");
    expect(INSUFFICIENT_HEADLINE.toLowerCase()).not.toContain("temperature");
    expect(INSUFFICIENT_SUPPORTS).toContain("Use other evidence");
    expect(INSUFFICIENT_SUPPORTS).toContain("Do not use thermal ranking alone");
    expect(INSUFFICIENT_DOES_NOT).toContain("not an all-clear");
    expect(INSUFFICIENT_DOES_NOT).not.toMatch(/error|blocked|failure/i);
  });

  it("keeps primary story copy free of debug chrome", () => {
    const blob = publishedStoryCopy().join("\n");
    for (const token of FORBIDDEN_STORY_CHROME) {
      expect(blob.toLowerCase()).not.toContain(token.toLowerCase());
    }
    expect(blob).not.toMatch(/0\.\d{8,}/);
    expect(blob.toLowerCase()).not.toContain("heattose");
    expect(blob).not.toMatch(/%/);
  });
});
