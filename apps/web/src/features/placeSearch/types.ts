/** Accountless Census Place search types. Fixture-typed. Not a published API. */

export const CENSUS_PLACE_VINTAGE = "US_CENSUS_GAZETTEER.PLACE.2025" as const;
export const NATIONAL_GEOGRAPHY_PACKAGE = "NATIONAL_GEOGRAPHY_PACKAGE_V1" as const;
export const GEOGRAPHY_CONTRACT = "hva-signal-public-geography-v1" as const;
export const RESOLVER_POLICY_ID = "NATIONAL_PLACE_GEOGRAPHY_V1" as const;
export const NATIONAL_AREA_ID_PREFIX = "us-place-";
export const NATIONAL_AREA_ID_SUFFIX = "-2025-national-place-geography-v1";
export const PHOENIX_DEMO_AREA_ID = "phoenix-demo";
export const NATIONAL_PHOENIX_AZ_GEOID = "0455000";
export const EXPECTED_ZONE_COUNT = 25;

export type PlaceType = "incorporated" | "cdp" | "consolidated_city_balance";
export type PlaceScope =
  | "conus_plus_dc"
  | "alaska"
  | "hawaii"
  | "puerto_rico"
  | "island_area";

export type CensusPlace = {
  place_geoid: string;
  place_name: string;
  official_name: string;
  state_abbreviation: string;
  state_fips: string;
  display_name: string;
  place_type: PlaceType;
  scope: PlaceScope;
  resolution_eligible: boolean;
  source_vintage: typeof CENSUS_PLACE_VINTAGE;
};

export type PlaceSearchOutcome =
  | { kind: "idle" }
  | { kind: "querying"; query: string; candidates: CensusPlace[] }
  | { kind: "ambiguous"; query: string; candidates: CensusPlace[] }
  | { kind: "unknown"; query: string }
  | { kind: "unique"; query: string; place: CensusPlace };

export type PlaceStatus =
  | "PLACE_IDLE"
  | "PLACE_QUERYING"
  | "PLACE_AMBIGUOUS"
  | "PLACE_UNKNOWN"
  | "PLACE_SELECTED"
  | "PLACE_LEGACY_PHOENIX_DEMO";

export type GeographyStatus =
  | "GEO_UNRESOLVED"
  | "GEO_RESOLVING"
  | "GEO_READY"
  | "GEO_UNSUPPORTED"
  | "GEO_FAILED";

export type ReferenceReadiness = "NOT_PREPARED";

export type UnsupportedGeographyReason =
  | "UNSUPPORTED_SCOPE"
  | "INSUFFICIENT_ELIGIBLE_TRACTS"
  | "INSUFFICIENT_CONNECTED_TRACTS"
  | "MULTI_TIMEZONE_AOI"
  | "UNKNOWN_PLACE"
  | "AMBIGUOUS_PLACE";

export type ResolvedGeography = {
  area_id: string;
  place: CensusPlace;
  expected_zone_count: typeof EXPECTED_ZONE_COUNT;
  zone_ids: string[];
  timezone: string;
  resolver_policy_id: typeof RESOLVER_POLICY_ID;
  aggregation_spec_version: string;
  area_selection_policy_version: string;
  package_schema: typeof NATIONAL_GEOGRAPHY_PACKAGE;
  geometry_sha256: string;
  display_label: string;
  analysis_window_caption: string;
  reference_readiness: ReferenceReadiness;
  historical_signal_capable: false;
};

export type RouteId = "national" | "phoenix-demo";

/** Named product scenes this surface owns, plus GEO_READY composition. */
export type ProductScene =
  | "open_search"
  | "place_ambiguous"
  | "place_unknown"
  | "resolving"
  | "unsupported_geography"
  | "analysis_window";

export type FixtureSceneId =
  | "open_search"
  | "place_ambiguous"
  | "place_unknown"
  | "resolving"
  | "unsupported_geography";

export type PlaceSearchState = {
  route: RouteId;
  query: string;
  place_status: PlaceStatus;
  selected_place: CensusPlace | null;
  candidates: CensusPlace[];
  geography_status: GeographyStatus;
  geography: ResolvedGeography | null;
  unsupported_reason: UnsupportedGeographyReason | null;
  unsupported_message: string | null;
  reference_readiness: ReferenceReadiness;
  fixture_scene: FixtureSceneId | null;
};

export type PlaceSearchEvent =
  | { type: "QUERY_CHANGED"; query: string }
  | { type: "SELECT_PLACE"; place: CensusPlace }
  | { type: "CLEAR_PLACE" }
  | { type: "OPEN_LEGACY_PHOENIX_DEMO" }
  | { type: "LEAVE_LEGACY_PHOENIX_DEMO" }
  | { type: "GEOGRAPHY_RESOLVED"; geography: ResolvedGeography }
  | {
      type: "GEOGRAPHY_UNSUPPORTED";
      reason: UnsupportedGeographyReason;
      message: string;
    }
  | { type: "GEOGRAPHY_FAILED"; message: string }
  | { type: "APPLY_SCENE"; scene: FixtureSceneId };

export function nationalAreaId(placeGeoid: string): string {
  return `${NATIONAL_AREA_ID_PREFIX}${placeGeoid}${NATIONAL_AREA_ID_SUFFIX}`;
}

export function isPhoenixDemoAreaId(areaId: string): boolean {
  return areaId === PHOENIX_DEMO_AREA_ID;
}

export function isNationalPhoenixAz(place: CensusPlace): boolean {
  return place.place_geoid === NATIONAL_PHOENIX_AZ_GEOID;
}
