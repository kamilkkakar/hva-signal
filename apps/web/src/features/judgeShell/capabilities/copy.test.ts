import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  ACTION_MATURITY,
  AFTERHEAT_MATURITY,
  CAPABILITY_KICKER,
  CAPABILITY_TITLE,
  FAKE_TIMELINE_LABELS,
  FORBIDDEN_CAPABILITY_PHRASES,
  GEOGRAPHY_MATURITY,
  HEATDOSE_MATURITY,
  HOSTED_LIVE_MATURITY,
  PLACE_SEARCH_MATURITY,
  PROBABILITY_MATURITY,
  SIGNAL_A_MATURITY,
  SIGNAL_B_MATURITY,
  WBGT_MATURITY,
  publishedCapabilityCopy,
  unpublishedNumericCopy,
} from "./copy";

const here = path.dirname(fileURLToPath(import.meta.url));
const css = readFileSync(path.join(here, "capabilities.css"), "utf8");

describe("capability expansion copy lock", () => {
  it("uses the compact chrome title, not a roadmap label", () => {
    expect(CAPABILITY_KICKER).toBe("Active capability expansion");
    expect(CAPABILITY_TITLE).toBe("Beyond a snapshot");
    const blob = publishedCapabilityCopy().join("\n").toLowerCase();
    expect(blob).not.toContain("future features");
    expect(blob).not.toContain("coming someday");
    expect(blob).not.toContain("roadmap only");
  });

  it("freezes Wave 2 maturity phrases", () => {
    expect(SIGNAL_A_MATURITY).toBe("AVAILABLE NOW");
    expect(SIGNAL_B_MATURITY).toBe("AVAILABLE NOW — CACHED EVIDENCE");
    expect(HEATDOSE_MATURITY).toBe("ANALYTICAL DEVELOPMENT");
    expect(AFTERHEAT_MATURITY).toBe("ACTIVE DEVELOPMENT & VALIDATION");
    expect(WBGT_MATURITY).toBe("INTEGRATION PATHWAY / BLOCKED inputs");
    expect(PROBABILITY_MATURITY).toBe("MODEL DEVELOPMENT, numeric BLOCKED");
    expect(ACTION_MATURITY).toBe("AVAILABLE NOW — DECISION FRAMING");
    expect(PLACE_SEARCH_MATURITY).toBe("DISABLED");
    expect(GEOGRAPHY_MATURITY).toBe("DISABLED");
    expect(HOSTED_LIVE_MATURITY).toBe("DISABLED");
  });

  it("promotes B only as cached evidence and keeps search/geo/live unpublished", () => {
    expect(SIGNAL_B_MATURITY).toBe("AVAILABLE NOW — CACHED EVIDENCE");
    expect(SIGNAL_B_MATURITY).not.toMatch(/\bLIVE\b/);
    expect(SIGNAL_B_MATURITY).not.toContain("CURRENT CONDITIONS");
    expect(PLACE_SEARCH_MATURITY).not.toContain("AVAILABLE NOW");
    expect(GEOGRAPHY_MATURITY).not.toContain("AVAILABLE NOW");
    expect(HOSTED_LIVE_MATURITY).not.toContain("AVAILABLE NOW");
    expect(HEATDOSE_MATURITY).not.toContain("AVAILABLE NOW");
    expect(AFTERHEAT_MATURITY).not.toContain("AVAILABLE NOW");
    expect(WBGT_MATURITY).not.toContain("AVAILABLE NOW");
    expect(PROBABILITY_MATURITY).not.toContain("AVAILABLE NOW");
  });

  it("keeps HeatDose, AfterHeat, WBGT, and probability free of numbers", () => {
    const blob = unpublishedNumericCopy().join("\n");
    expect(blob).not.toMatch(/\d/);
    expect(blob).not.toMatch(/%/);
    expect(blob.toLowerCase()).not.toContain("overnight recovery");
  });

  it("forbids overclaim and fake-mode language", () => {
    const blob = publishedCapabilityCopy().join("\n").toLowerCase();
    for (const phrase of FORBIDDEN_CAPABILITY_PHRASES) {
      expect(blob.includes(phrase)).toBe(false);
    }
    for (const label of FAKE_TIMELINE_LABELS) {
      expect(publishedCapabilityCopy().includes(label)).toBe(false);
    }
  });

  it("wraps instead of introducing a horizontal gauge strip", () => {
    expect(css).toContain("min-width: 0");
    expect(css).toContain("overflow-wrap: anywhere");
    expect(css).toContain("grid-template-columns: repeat(3, minmax(0, 1fr))");
    expect(css).not.toContain("progress");
    expect(css).not.toContain("meter");
    expect(css).not.toMatch(/(?<![-\w])width:\s*\d+%/);
  });
});
