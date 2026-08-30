/** Frozen-candidate copy. B1/B3 remain human-open — do not label this FROZEN. */

import { RESOLVER_POLICY_ID, type CensusPlace } from "./types";

export const PRODUCT_NAME = "HVA-Signal";
export const PRODUCT_EXPANSION = "Heat, Vulnerability & Action Signal";

export const SEARCH_LABEL = "Census Place name or 7-digit GEOID";
export const SEARCH_HINT =
  "Search a 2025 Census Place, then select the canonical row. Bare names such as Springfield or Phoenix stay ambiguous until a state or GEOID is chosen.";
export const SEARCH_PLACEHOLDER = "Chicago, IL";

export const AMBIGUOUS_PLACE_COPY =
  "More than one Census Place matches that name. HVA-Signal does not pick a largest city. Specify a state (`Name, ST`) or a 7-digit place GEOID.";

export const UNKNOWN_PLACE_COPY =
  "No 2025 Census Place matches that query. County subdivisions and metropolitan areas are not Census Places.";

export const RESOLVING_COPY =
  "Resolving the 25-zone analysis window for the selected Census place. This is not city-wide coverage.";

export const UNSUPPORTED_GEOGRAPHY_COPY =
  "This Census place cannot become an HVA-Signal 25-zone analysis geography in v1.";

export const GEOGRAPHY_READY_COPY =
  "A 25-zone HVA-Signal analysis geography is ready for this analysis window.";

export const REFERENCE_NOT_PREPARED_COPY =
  "Historical reference is not prepared. Signal A, Decision 8, and thermal ranking are unavailable. Missing reference is not treated as safe.";

export const GEOGRAPHY_REFERENCE_SPLIT_COPY =
  "Geography is ready: a 25-zone HVA-Signal analysis geography exists for this analysis window. Historical reference is not prepared. Thermal ranking is not evaluated.";

export const B1_B3_DISCLOSURE =
  "This 25-zone window is a compact analysis geography inside the selected Census place. It is not municipal coverage, not the entire place, and not a unique city shape. Seed and growth rules can yield a different window. That product claim remains human-open (B1/B3) and is not frozen.";

export const NO_COMBINED_SCORE_COPY =
  "Signal A and Signal B stay independent. A combined score is not authorized.";

export const NOT_THERMAL_PRODUCT_COPY =
  "Census Place search resolves an analysis geography only. It is not a thermal product and does not imply coverage, ranking, or a selected-time snapshot.";

export const PHOENIX_DEMO_LEGACY_LABEL = "Phoenix-demo (legacy replay)";
export const PHOENIX_DEMO_LEGACY_COPY =
  "Phoenix-demo is a distinct legacy historical replay. It is not the national Phoenix, AZ Census place and is not replaced by searching Phoenix, AZ.";

export const NATIONAL_SEARCH_LABEL = "National Census Place search";

export const OPEN_SEARCH_STAGE_COPY =
  "Select a canonical 2025 Census Place to resolve a 25-zone analysis window. The map will not invent municipal coverage.";

export const GEO_CHIP_GEOGRAPHY_READY = "Geography ready";
export const GEO_CHIP_REFERENCE_NOT_PREPARED = "Reference not prepared";

export const FIXTURE_SWITCHER_LABEL = "IA fixtures — not a published API";

export function analysisWindowCopy(placeDisplayName: string): string {
  return `25-zone analysis window within ${placeDisplayName}`;
}

export function analysisGeographyCopy(placeDisplayName: string): string {
  return `HVA-Signal 25-zone analysis geography for ${placeDisplayName}`;
}

export function displayLabel(place: CensusPlace): string {
  return `HVA-Signal 25-zone analysis geography for ${place.official_name}, ${place.state_abbreviation}`;
}

export function analysisWindowCaption(place: CensusPlace): string {
  return `25-zone HVA-Signal analysis geography — analysis window within ${place.official_name}, ${place.state_abbreviation}, generated under resolver policy ${RESOLVER_POLICY_ID}`;
}

export function unsupportedScopeMessage(place: CensusPlace): string {
  return `${place.official_name} is outside the CONUS+DC analysis scope under resolver policy ${RESOLVER_POLICY_ID}.`;
}

export function insufficientEligibleMessage(place: CensusPlace): string {
  return `${place.official_name}, ${place.state_abbreviation} has fewer than 25 eligible census tracts under resolver policy ${RESOLVER_POLICY_ID}. HVA-Signal will not invent zones. This does not mean the place is or is not a city.`;
}

export function insufficientConnectedMessage(place: CensusPlace): string {
  return `The seed-component analysis window within ${place.official_name}, ${place.state_abbreviation} has fewer than 25 connected eligible tracts under resolver policy ${RESOLVER_POLICY_ID}. HVA-Signal does not jump to another island or add land outside the Census Place.`;
}

export function multiTimezoneMessage(place: CensusPlace): string {
  return `The 25-zone analysis window within ${place.official_name}, ${place.state_abbreviation} spans more than one IANA timezone. HVA-Signal does not majority-vote a timezone. This analysis window is not supported under resolver policy ${RESOLVER_POLICY_ID}.`;
}

export const FORBIDDEN_CITYWIDE_PHRASES = [
  "the geography of",
  "city-wide",
  "citywide",
  "entire city",
  "city coverage",
  "chicago's zones",
] as const;

export const FORBIDDEN_AUTH_PHRASES = [
  "log in",
  "login",
  "sign up",
  "signup",
  "create account",
  "my account",
  "persona",
] as const;

export const FORBIDDEN_THERMAL_COVERAGE_PHRASES = [
  "thermal coverage",
  "city-wide heat",
  "ranked heat map",
  "supported city",
] as const;
