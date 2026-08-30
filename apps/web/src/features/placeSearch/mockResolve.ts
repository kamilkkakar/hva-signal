import {
  PLACE_RESOLVE_KIND,
  buildResolvedGeography,
  unsupportedMessageFor,
} from "../../mocks/placeSearchFixtures";
import {
  insufficientConnectedMessage,
  multiTimezoneMessage,
} from "./copy";
import type { CensusPlace, PlaceSearchEvent, UnsupportedGeographyReason } from "./types";

export const MOCK_RESOLVE_DELAY_MS = 420;

export function mockResolveGeography(place: CensusPlace): PlaceSearchEvent {
  const kind = PLACE_RESOLVE_KIND[place.place_geoid] ?? "UNKNOWN_PLACE";
  if (kind === "ready") {
    return { type: "GEOGRAPHY_RESOLVED", geography: buildResolvedGeography(place) };
  }
  return {
    type: "GEOGRAPHY_UNSUPPORTED",
    reason: kind,
    message: unsupportedCopy(place, kind),
  };
}

function unsupportedCopy(
  place: CensusPlace,
  reason: UnsupportedGeographyReason,
): string {
  if (reason === "INSUFFICIENT_CONNECTED_TRACTS") {
    return insufficientConnectedMessage(place);
  }
  if (reason === "MULTI_TIMEZONE_AOI") {
    return multiTimezoneMessage(place);
  }
  if (reason === "UNKNOWN_PLACE") {
    return "No matching 2025 Census Place.";
  }
  if (reason === "AMBIGUOUS_PLACE") {
    return "More than one 2025 Census Place matches. Select a canonical row.";
  }
  return unsupportedMessageFor(place, reason);
}
