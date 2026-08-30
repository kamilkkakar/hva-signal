import {
  analysisWindowCaption,
  displayLabel,
  insufficientEligibleMessage,
  unsupportedScopeMessage,
} from "../features/placeSearch/copy";
import {
  CENSUS_PLACE_VINTAGE,
  EXPECTED_ZONE_COUNT,
  NATIONAL_GEOGRAPHY_PACKAGE,
  RESOLVER_POLICY_ID,
  nationalAreaId,
  type CensusPlace,
  type FixtureSceneId,
  type PlaceSearchState,
  type PlaceType,
  type PlaceScope,
  type ResolvedGeography,
  type UnsupportedGeographyReason,
} from "../features/placeSearch/types";

function place(
  row: Omit<CensusPlace, "display_name" | "source_vintage" | "resolution_eligible"> & {
    resolution_eligible?: boolean;
  },
): CensusPlace {
  return {
    ...row,
    display_name: `${row.place_name}, ${row.state_abbreviation}`,
    source_vintage: CENSUS_PLACE_VINTAGE,
    resolution_eligible: row.resolution_eligible ?? row.scope === "conus_plus_dc",
  };
}

/** Official 2025 Gazetteer identity rows used as typed search fixtures. */
export const PLACE_INDEX: readonly CensusPlace[] = [
  place({
    place_geoid: "1714000",
    place_name: "Chicago",
    official_name: "Chicago city",
    state_abbreviation: "IL",
    state_fips: "17",
    place_type: "incorporated" satisfies PlaceType,
    scope: "conus_plus_dc" satisfies PlaceScope,
  }),
  place({
    place_geoid: "1772000",
    place_name: "Springfield",
    official_name: "Springfield city",
    state_abbreviation: "IL",
    state_fips: "17",
    place_type: "incorporated",
    scope: "conus_plus_dc",
  }),
  place({
    place_geoid: "2970000",
    place_name: "Springfield",
    official_name: "Springfield city",
    state_abbreviation: "MO",
    state_fips: "29",
    place_type: "incorporated",
    scope: "conus_plus_dc",
  }),
  place({
    place_geoid: "0455000",
    place_name: "Phoenix",
    official_name: "Phoenix city",
    state_abbreviation: "AZ",
    state_fips: "04",
    place_type: "incorporated",
    scope: "conus_plus_dc",
  }),
  place({
    place_geoid: "4157500",
    place_name: "Phoenix",
    official_name: "Phoenix city",
    state_abbreviation: "OR",
    state_fips: "41",
    place_type: "incorporated",
    scope: "conus_plus_dc",
  }),
  place({
    place_geoid: "1759572",
    place_name: "Phoenix",
    official_name: "Phoenix village",
    state_abbreviation: "IL",
    state_fips: "17",
    place_type: "incorporated",
    scope: "conus_plus_dc",
  }),
  place({
    place_geoid: "3657661",
    place_name: "Phoenix",
    official_name: "Phoenix village",
    state_abbreviation: "NY",
    state_fips: "36",
    place_type: "incorporated",
    scope: "conus_plus_dc",
  }),
  place({
    place_geoid: "0203000",
    place_name: "Anchorage",
    official_name: "Anchorage municipality",
    state_abbreviation: "AK",
    state_fips: "02",
    place_type: "incorporated",
    scope: "alaska",
    resolution_eligible: false,
  }),
  place({
    place_geoid: "1571550",
    place_name: "Urban Honolulu",
    official_name: "Urban Honolulu CDP",
    state_abbreviation: "HI",
    state_fips: "15",
    place_type: "cdp",
    scope: "hawaii",
    resolution_eligible: false,
  }),
];

function requirePlace(placeGeoid: string): CensusPlace {
  const found = PLACE_INDEX.find((row) => row.place_geoid === placeGeoid);
  if (!found) {
    throw new Error(`Missing fixture place ${placeGeoid}`);
  }
  return found;
}

export const CHICAGO_IL = requirePlace("1714000");
export const SPRINGFIELD_IL = requirePlace("1772000");
export const SPRINGFIELD_MO = requirePlace("2970000");
export const PHOENIX_AZ_NATIONAL = requirePlace("0455000");
export const PHOENIX_OR = requirePlace("4157500");
export const ANCHORAGE_AK = requirePlace("0203000");
export const URBAN_HONOLULU_HI = requirePlace("1571550");

export type PlaceResolveKind = "ready" | UnsupportedGeographyReason;

export const PLACE_RESOLVE_KIND: Record<string, PlaceResolveKind> = {
  "1714000": "ready",
  "1772000": "ready",
  "2970000": "ready",
  "0455000": "ready",
  "4157500": "ready",
  "1759572": "INSUFFICIENT_ELIGIBLE_TRACTS",
  "3657661": "INSUFFICIENT_ELIGIBLE_TRACTS",
  "0203000": "UNSUPPORTED_SCOPE",
  "1571550": "UNSUPPORTED_SCOPE",
};

const PLACE_TIMEZONE: Record<string, string> = {
  "1714000": "America/Chicago",
  "1772000": "America/Chicago",
  "2970000": "America/Chicago",
  "0455000": "America/Phoenix",
  "4157500": "America/Los_Angeles",
};

export function fixtureZoneIds(placeGeoid: string): string[] {
  return Array.from({ length: EXPECTED_ZONE_COUNT }, (_, index) => {
    const n = String(index + 1).padStart(2, "0");
    return `FIX-${placeGeoid}-${n}`;
  });
}

export function fixtureGeometrySha(placeGeoid: string): string {
  const seed = `hva-signal-fixture-geography-${placeGeoid}`;
  let hex = "";
  for (let i = 0; i < 64; i += 1) {
    hex += (seed.charCodeAt(i % seed.length) % 16).toString(16);
  }
  return hex;
}

export function buildResolvedGeography(selected: CensusPlace): ResolvedGeography {
  return {
    area_id: nationalAreaId(selected.place_geoid),
    place: selected,
    expected_zone_count: EXPECTED_ZONE_COUNT,
    zone_ids: fixtureZoneIds(selected.place_geoid),
    timezone: PLACE_TIMEZONE[selected.place_geoid] ?? "America/Chicago",
    resolver_policy_id: RESOLVER_POLICY_ID,
    aggregation_spec_version: "HVA_NATIONAL_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN",
    area_selection_policy_version: "ALG1_GREEDY_LEX_PLACE_INTPT_V1",
    package_schema: NATIONAL_GEOGRAPHY_PACKAGE,
    geometry_sha256: fixtureGeometrySha(selected.place_geoid),
    display_label: displayLabel(selected),
    analysis_window_caption: analysisWindowCaption(selected),
    reference_readiness: "NOT_PREPARED",
    historical_signal_capable: false,
  };
}

export function initialPlaceSearchState(): PlaceSearchState {
  return {
    route: "national",
    query: "",
    place_status: "PLACE_IDLE",
    selected_place: null,
    candidates: [],
    geography_status: "GEO_UNRESOLVED",
    geography: null,
    unsupported_reason: null,
    unsupported_message: null,
    reference_readiness: "NOT_PREPARED",
    fixture_scene: "open_search",
  };
}

export const FIXTURE_SCENE_LABELS: Record<FixtureSceneId, string> = {
  open_search: "Open app / search",
  place_ambiguous: "Ambiguous place",
  place_unknown: "Unknown place",
  resolving: "Resolving geography",
  unsupported_geography: "Unsupported geography",
};

export function sceneSnapshot(scene: FixtureSceneId): PlaceSearchState {
  const base = initialPlaceSearchState();
  if (scene === "open_search") {
    return { ...base, fixture_scene: scene };
  }
  if (scene === "place_ambiguous") {
    return {
      ...base,
      query: "Phoenix",
      place_status: "PLACE_AMBIGUOUS",
      candidates: PLACE_INDEX.filter((row) => row.place_name === "Phoenix"),
      fixture_scene: scene,
    };
  }
  if (scene === "place_unknown") {
    return {
      ...base,
      query: "Glastonbury, CT",
      place_status: "PLACE_UNKNOWN",
      fixture_scene: scene,
    };
  }
  if (scene === "resolving") {
    return {
      ...base,
      query: "Chicago, IL",
      place_status: "PLACE_SELECTED",
      selected_place: CHICAGO_IL,
      candidates: [CHICAGO_IL],
      geography_status: "GEO_RESOLVING",
      fixture_scene: scene,
    };
  }
  return {
    ...base,
    query: "Anchorage, AK",
    place_status: "PLACE_SELECTED",
    selected_place: ANCHORAGE_AK,
    candidates: [ANCHORAGE_AK],
    geography_status: "GEO_UNSUPPORTED",
    unsupported_reason: "UNSUPPORTED_SCOPE",
    unsupported_message: unsupportedScopeMessage(ANCHORAGE_AK),
    fixture_scene: scene,
  };
}

export function unsupportedMessageFor(
  placeRow: CensusPlace,
  reason: UnsupportedGeographyReason,
): string {
  if (reason === "UNSUPPORTED_SCOPE") {
    return unsupportedScopeMessage(placeRow);
  }
  if (reason === "INSUFFICIENT_ELIGIBLE_TRACTS") {
    return insufficientEligibleMessage(placeRow);
  }
  return unsupportedScopeMessage(placeRow);
}
