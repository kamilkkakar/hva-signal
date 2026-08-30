import { describe, expect, it } from "vitest";
import {
  AMBIGUOUS_PLACE_COPY,
  B1_B3_DISCLOSURE,
  FORBIDDEN_AUTH_PHRASES,
  FORBIDDEN_CITYWIDE_PHRASES,
  FORBIDDEN_THERMAL_COVERAGE_PHRASES,
  GEOGRAPHY_REFERENCE_SPLIT_COPY,
  NOT_THERMAL_PRODUCT_COPY,
  PHOENIX_DEMO_LEGACY_COPY,
  SEARCH_LABEL,
  UNKNOWN_PLACE_COPY,
  analysisGeographyCopy,
  analysisWindowCaption,
  analysisWindowCopy,
  displayLabel,
} from "./copy";
import { CHICAGO_IL, PHOENIX_AZ_NATIONAL } from "../../mocks/placeSearchFixtures";

const PUBLISHED_COPY = [
  SEARCH_LABEL,
  analysisWindowCopy("Chicago, IL"),
  analysisGeographyCopy("Chicago, IL"),
  displayLabel(CHICAGO_IL),
  analysisWindowCaption(CHICAGO_IL),
  displayLabel(PHOENIX_AZ_NATIONAL),
  analysisWindowCaption(PHOENIX_AZ_NATIONAL),
  B1_B3_DISCLOSURE,
  PHOENIX_DEMO_LEGACY_COPY,
  GEOGRAPHY_REFERENCE_SPLIT_COPY,
  NOT_THERMAL_PRODUCT_COPY,
  AMBIGUOUS_PLACE_COPY,
  UNKNOWN_PLACE_COPY,
];

describe("frozen-candidate geography copy", () => {
  it("uses Census Place as the noun, not city", () => {
    expect(SEARCH_LABEL).toBe("Census Place name or 7-digit GEOID");
    expect(SEARCH_LABEL.toLowerCase()).not.toContain("city");
    expect(displayLabel(CHICAGO_IL)).toBe(
      "HVA-Signal 25-zone analysis geography for Chicago city, IL",
    );
    expect(analysisWindowCaption(CHICAGO_IL)).toContain(
      "analysis window within Chicago city, IL",
    );
    expect(analysisWindowCaption(CHICAGO_IL)).toContain(
      "generated under resolver policy NATIONAL_PLACE_GEOGRAPHY_V1",
    );
  });

  it("never uses city-wide or city-equivalence phrasing as a claim", () => {
    const blob = PUBLISHED_COPY.join("\n").toLowerCase();
    for (const phrase of FORBIDDEN_CITYWIDE_PHRASES) {
      expect(blob.includes(phrase)).toBe(false);
    }
    expect(blob).not.toContain("the geography of chicago");
    expect(blob).not.toContain("the geography of phoenix");
  });

  it("never implies login, signup, account, or persona", () => {
    const blob = PUBLISHED_COPY.join("\n").toLowerCase();
    for (const phrase of FORBIDDEN_AUTH_PHRASES) {
      expect(blob.includes(phrase)).toBe(false);
    }
  });

  it("does not imply thermal coverage", () => {
    const blob = PUBLISHED_COPY.join("\n").toLowerCase();
    for (const phrase of FORBIDDEN_THERMAL_COVERAGE_PHRASES) {
      expect(blob.includes(phrase)).toBe(false);
    }
    expect(blob).toContain("thermal ranking is not evaluated");
    expect(blob).toContain("not a thermal product");
  });

  it("keeps phoenix-demo distinct from national Phoenix, AZ", () => {
    expect(PHOENIX_DEMO_LEGACY_COPY.toLowerCase()).toContain("phoenix-demo");
    expect(PHOENIX_DEMO_LEGACY_COPY.toLowerCase()).toContain("not the national");
    expect(analysisWindowCaption(PHOENIX_AZ_NATIONAL)).toContain("Phoenix city, AZ");
    expect(analysisWindowCaption(PHOENIX_AZ_NATIONAL)).not.toContain("phoenix-demo");
  });

  it("keeps B1/B3 human-open", () => {
    expect(B1_B3_DISCLOSURE.toLowerCase()).toContain("human-open");
    expect(B1_B3_DISCLOSURE.toLowerCase()).not.toContain("status: frozen");
  });
});
