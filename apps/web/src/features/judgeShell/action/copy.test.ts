import { describe, expect, it } from "vitest";
import {
  FORBIDDEN_ACTION_PHRASES,
  INSUFFICIENT_DOES_NOT_COPY,
  INSUFFICIENT_SAYS_COPY,
  INSUFFICIENT_SUPPORTS_COPY,
  REQUIRED_CONTEXT_COPY,
  SUFFICIENT_DOES_NOT_COPY,
  SUFFICIENT_SAYS_COPY,
  SUFFICIENT_SUPPORTS_COPY,
  publishedActionCopy,
} from "./copy";

describe("Action v0 copy lock", () => {
  it("frames sufficient as one input, not automatic deployment", () => {
    expect(SUFFICIENT_SAYS_COPY).toContain("supports spatial ordering");
    expect(SUFFICIENT_SAYS_COPY).toContain("frozen historical signal protocol");
    expect(SUFFICIENT_SUPPORTS_COPY).toContain("one input");
    expect(SUFFICIENT_DOES_NOT_COPY).toContain("does not authorize automatic deployment");
    expect(SUFFICIENT_DOES_NOT_COPY).toContain(REQUIRED_CONTEXT_COPY);
  });

  it("frames insufficient as withhold, not all-clear", () => {
    expect(INSUFFICIENT_SAYS_COPY).toContain("does not support a defensible spatial ordering");
    expect(INSUFFICIENT_SUPPORTS_COPY).toBe(
      "Do not use thermal ranking alone for zone prioritization.",
    );
    expect(INSUFFICIENT_DOES_NOT_COPY).toContain("not a safety clearance");
    expect(INSUFFICIENT_DOES_NOT_COPY).toContain("does not mean zones have equal need");
    expect(INSUFFICIENT_DOES_NOT_COPY).toContain(REQUIRED_CONTEXT_COPY);
  });

  it("requires remaining context layers and forbids efficacy language", () => {
    const blob = publishedActionCopy().join("\n").toLowerCase();
    expect(blob).toContain("vulnerability");
    expect(blob).toContain("preparedness");
    expect(blob).toContain("operational constraints");
    expect(blob).toContain("local context");
    expect(blob).not.toMatch(/%/);
    expect(blob).not.toContain("fortyguard");
    expect(blob).not.toContain("q_a");
    expect(blob).not.toContain("wbgt");
    expect(blob).not.toContain("heatdose");
    for (const phrase of FORBIDDEN_ACTION_PHRASES) {
      expect(blob.includes(phrase)).toBe(false);
    }
  });
});
