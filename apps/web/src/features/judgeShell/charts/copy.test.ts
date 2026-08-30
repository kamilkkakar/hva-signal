import { describe, expect, it } from "vitest";
import {
  AXIS_HIGH,
  AXIS_LOW,
  FORBIDDEN_CHART_CHROME,
  STAMP_ORDERING_SUPPORTED,
  STAMP_ORDERING_WITHHELD,
  publishedChartChrome,
} from "./copy";

describe("chart copy lock", () => {
  it("pins the historical-position axis and binary comparison state", () => {
    expect(AXIS_LOW).toBe("LOWER POSITION IN OWN HISTORY");
    expect(AXIS_HIGH).toBe("HIGHER POSITION IN OWN HISTORY");
    expect(STAMP_ORDERING_SUPPORTED).toBe("ORDERING SUPPORTED");
    expect(STAMP_ORDERING_WITHHELD).toBe("ORDERING WITHHELD");
  });

  it("keeps probability, method nouns, and qualitative bands off chrome copy", () => {
    const chrome = publishedChartChrome().join("\n");
    for (const token of FORBIDDEN_CHART_CHROME) {
      expect(chrome.includes(token), token).toBe(false);
    }
    expect(chrome).not.toMatch(/%/);
  });
});
