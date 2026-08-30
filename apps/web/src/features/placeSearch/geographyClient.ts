import { GEOGRAPHY_CONTRACT, type CensusPlace, type PlaceSearchEvent, type PlaceSearchOutcome } from "./types";
import { isPlaceSearchApiEnabled } from "./flags";
import { mockResolveGeography } from "./mockResolve";
import { searchCensusPlaces } from "./search";

type PlaceCandidateDto = {
  place_geoid: string;
  official_name: string;
  place_name: string;
  display_name: string;
  state_fips: string;
  state_abbreviation: string;
  place_type: CensusPlace["place_type"];
  scope: CensusPlace["scope"];
  resolution_eligible: boolean;
};

type PlaceSearchResponseDto = {
  query: string;
  matches: PlaceCandidateDto[];
  reason: { code: string; message: string } | null;
};

type GeographyDocumentDto = {
  area_id: string;
  supported: boolean | null;
  geography_readiness: string;
  resolution_outcome: string;
  display_label?: string;
  analysis_window_caption?: string;
  reason?: { code: string; message: string } | null;
  place?: PlaceCandidateDto;
  identity?: {
    timezone?: string;
    geometry_sha256?: string;
    zone_geoids?: string[];
  };
};

function toCensusPlace(row: PlaceCandidateDto): CensusPlace {
  return {
    place_geoid: row.place_geoid,
    place_name: row.place_name,
    official_name: row.official_name,
    state_abbreviation: row.state_abbreviation,
    state_fips: row.state_fips,
    display_name: row.display_name,
    place_type: row.place_type,
    scope: row.scope,
    resolution_eligible: row.resolution_eligible,
    source_vintage: "US_CENSUS_GAZETTEER.PLACE.2025",
  };
}

/** Search never starts resolve. API flag OFF → typed Gazetteer fixtures. */
export function lookupPlaces(query: string): PlaceSearchOutcome {
  return searchCensusPlaces(query);
}

export async function lookupPlacesAsync(query: string): Promise<PlaceSearchOutcome> {
  if (!isPlaceSearchApiEnabled()) {
    return searchCensusPlaces(query);
  }
  const url = `/api/v1/places?q=${encodeURIComponent(query)}`;
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    return { kind: "unknown", query };
  }
  const body = (await response.json()) as PlaceSearchResponseDto;
  const matches = (body.matches ?? []).map(toCensusPlace);
  if (matches.length === 0) {
    return { kind: "unknown", query };
  }
  if (matches.length === 1 && matches[0]) {
    return { kind: "unique", query, place: matches[0] };
  }
  return { kind: "ambiguous", query, candidates: matches };
}

export async function resolvePlaceGeography(place: CensusPlace): Promise<PlaceSearchEvent> {
  if (!isPlaceSearchApiEnabled()) {
    return mockResolveGeography(place);
  }
  const response = await fetch("/api/v1/geographies", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({
      contract_version: GEOGRAPHY_CONTRACT,
      place_geoid: place.place_geoid,
    }),
  });
  if (!response.ok && response.status !== 202) {
    return {
      type: "GEOGRAPHY_FAILED",
      message: "Geography resolve failed. This is not a thermal result.",
    };
  }
  const body = (await response.json()) as GeographyDocumentDto;
  return geographyDocumentToEvent(place, body);
}

function geographyDocumentToEvent(
  place: CensusPlace,
  body: GeographyDocumentDto,
): PlaceSearchEvent {
  if (body.resolution_outcome === "UNSUPPORTED" || body.supported === false) {
    return {
      type: "GEOGRAPHY_UNSUPPORTED",
      reason: (body.reason?.code as "UNSUPPORTED_SCOPE") ?? "UNSUPPORTED_SCOPE",
      message: body.reason?.message ?? "This Census Place cannot become a v1 analysis geography.",
    };
  }
  if (body.geography_readiness === "GEOGRAPHY_READY" && body.supported === true) {
    const mock = mockResolveGeography(place);
    if (mock.type !== "GEOGRAPHY_RESOLVED") {
      return mock;
    }
    return {
      type: "GEOGRAPHY_RESOLVED",
      geography: {
        ...mock.geography,
        area_id: body.area_id || mock.geography.area_id,
        display_label: body.display_label ?? mock.geography.display_label,
        analysis_window_caption:
          body.analysis_window_caption ?? mock.geography.analysis_window_caption,
        timezone: body.identity?.timezone ?? mock.geography.timezone,
        geometry_sha256: body.identity?.geometry_sha256 ?? mock.geography.geometry_sha256,
        zone_ids: body.identity?.zone_geoids ?? mock.geography.zone_ids,
      },
    };
  }
  return {
    type: "GEOGRAPHY_FAILED",
    message: "Geography document was not a supported analysis window. No thermal coverage is implied.",
  };
}
