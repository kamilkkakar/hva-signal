import { describe, expect, it } from "vitest";
import { PLACE_INDEX } from "../../mocks/placeSearchFixtures";
import { isPlaceSearchApiEnabled } from "./flags";
import { lookupPlaces } from "./geographyClient";
import { phoenixDemoIsSearchable, searchCensusPlaces } from "./search";
import { PHOENIX_DEMO_AREA_ID } from "./types";

describe("Census Place search", () => {
  it("keeps phoenix-demo out of the Census Place index", () => {
    expect(phoenixDemoIsSearchable()).toBe(false);
    expect(PLACE_INDEX.some((row) => row.place_geoid === PHOENIX_DEMO_AREA_ID)).toBe(
      false,
    );
    expect(searchCensusPlaces("phoenix-demo").kind).toBe("unknown");
    expect(searchCensusPlaces("Phoenix, AZ").kind).toBe("unique");
  });

  it("requires a state or GEOID for Phoenix and Springfield", () => {
    const phoenix = searchCensusPlaces("Phoenix");
    const springfield = searchCensusPlaces("Springfield");
    expect(phoenix.kind).toBe("ambiguous");
    expect(springfield.kind).toBe("ambiguous");
    if (phoenix.kind === "ambiguous") {
      expect(phoenix.candidates.some((row) => row.place_geoid === "0455000")).toBe(
        true,
      );
      expect(
        phoenix.candidates.every((row) => row.place_geoid !== PHOENIX_DEMO_AREA_ID),
      ).toBe(true);
    }
  });

  it("resolves Chicago, IL to the canonical Census Place", () => {
    const outcome = searchCensusPlaces("Chicago, IL");
    expect(outcome.kind).toBe("unique");
    if (outcome.kind === "unique") {
      expect(outcome.place.place_geoid).toBe("1714000");
      expect(outcome.place.display_name).toBe("Chicago, IL");
      expect(outcome.place.official_name).toBe("Chicago city");
    }
  });

  it("does not treat Glastonbury, CT as a Census Place", () => {
    expect(searchCensusPlaces("Glastonbury, CT").kind).toBe("unknown");
  });

  it("uses typed mocks while the unpublished API flag is off", () => {
    expect(isPlaceSearchApiEnabled()).toBe(false);
    expect(lookupPlaces("Phoenix")).toEqual(searchCensusPlaces("Phoenix"));
  });
});
