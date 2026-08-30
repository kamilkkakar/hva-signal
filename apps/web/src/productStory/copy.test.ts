import { describe, expect, it } from "vitest";
import {
  COMPARISON_SUFFICIENT,
  COMPARISON_TOO_SIMILAR,
  EVIDENCE_LINEAGE_RECORDED,
  FORBIDDEN_PUBLIC_TOKENS,
  REFERENCE_AVAILABLE,
  formatAreaLabel,
  formatObservationTime,
  formatOrderHover,
  formatReferenceYears,
  publishedStoryCopy,
} from "./copy";

describe("story copy lock", () => {
  it("pins the mandated backend-to-public mappings", () => {
    expect(COMPARISON_SUFFICIENT).toBe(
      "Spatial differences are clear enough to compare",
    );
    expect(COMPARISON_TOO_SIMILAR).toBe(
      "Temperatures are too similar across the area to support a defensible ordering",
    );
    expect(REFERENCE_AVAILABLE).toBe("Historical reference available");
    expect(EVIDENCE_LINEAGE_RECORDED).toBe("Evidence lineage recorded");
  });

  it("keeps published chrome free of backend status tokens", () => {
    const chrome = publishedStoryCopy()
      .filter((line) => line !== EVIDENCE_LINEAGE_RECORDED)
      .join("\n");
    for (const token of FORBIDDEN_PUBLIC_TOKENS) {
      expect(chrome.includes(token), token).toBe(false);
    }
  });

  it("formats observation time from the request date without inventing a clock", () => {
    expect(formatObservationTime("2022-06-30T03:00:00")).toBe(
      "2022-06-30 · 03:00 AOI-local · dated replay · not live",
    );
    expect(formatObservationTime(null)).toBe(
      "03:00 AOI-local · dated replay · not live",
    );
  });

  it("names phoenix-demo as an analysis window, not the municipality", () => {
    expect(formatAreaLabel("phoenix-demo")).toBe(
      "phoenix-demo — 25-zone analysis window, not the municipality",
    );
    expect(formatAreaLabel("phoenix-demo")).not.toMatch(/city-wide|Phoenix's heat/);
    expect(formatAreaLabel(null)).toBe("25-zone analysis window, not a city");
  });

  it("does not invent reference years", () => {
    expect(formatReferenceYears(undefined)).toBeNull();
    expect(formatReferenceYears([])).toBeNull();
    expect(formatReferenceYears([2020, 2022, 2021])).toBe("2020–2022");
  });

  it("states zone order without q_A or degrees", () => {
    const line = formatOrderHover("04013061000", 4);
    expect(line).toContain("Nighttime order 4 of 25");
    expect(line).not.toContain("q_A");
    expect(line).not.toMatch(/°C/);
  });
});
