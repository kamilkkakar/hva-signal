import {
  initialPlaceSearchState,
  sceneSnapshot,
} from "../../mocks/placeSearchFixtures";
import { candidatesForOutcome, searchCensusPlaces } from "./search";
import {
  isNationalPhoenixAz,
  isPhoenixDemoAreaId,
  type CensusPlace,
  type PlaceSearchEvent,
  type PlaceSearchState,
  type ProductScene,
} from "./types";

export function productScene(state: PlaceSearchState): ProductScene {
  if (state.place_status === "PLACE_LEGACY_PHOENIX_DEMO") {
    return "open_search";
  }
  if (state.geography_status === "GEO_RESOLVING") {
    return "resolving";
  }
  if (state.geography_status === "GEO_UNSUPPORTED" || state.geography_status === "GEO_FAILED") {
    return "unsupported_geography";
  }
  if (state.geography_status === "GEO_READY") {
    return "analysis_window";
  }
  if (state.place_status === "PLACE_AMBIGUOUS") {
    return "place_ambiguous";
  }
  if (state.place_status === "PLACE_UNKNOWN") {
    return "place_unknown";
  }
  return "open_search";
}

export function reducePlaceSearch(
  state: PlaceSearchState,
  event: PlaceSearchEvent,
): PlaceSearchState {
  switch (event.type) {
    case "APPLY_SCENE":
      return sceneSnapshot(event.scene);
    case "OPEN_LEGACY_PHOENIX_DEMO":
      return {
        ...initialPlaceSearchState(),
        route: "phoenix-demo",
        place_status: "PLACE_LEGACY_PHOENIX_DEMO",
        fixture_scene: null,
      };
    case "LEAVE_LEGACY_PHOENIX_DEMO":
      return initialPlaceSearchState();
    case "CLEAR_PLACE":
      return initialPlaceSearchState();
    case "QUERY_CHANGED":
      return applyQuery(state, event.query);
    case "SELECT_PLACE":
      return selectPlace(state, event.place);
    case "GEOGRAPHY_RESOLVED":
      return applyResolved(state, event);
    case "GEOGRAPHY_UNSUPPORTED":
      return {
        ...state,
        geography_status: "GEO_UNSUPPORTED",
        geography: null,
        unsupported_reason: event.reason,
        unsupported_message: event.message,
        reference_readiness: "NOT_PREPARED",
      };
    case "GEOGRAPHY_FAILED":
      return {
        ...state,
        geography_status: "GEO_FAILED",
        geography: null,
        unsupported_reason: null,
        unsupported_message: event.message,
        reference_readiness: "NOT_PREPARED",
      };
    default:
      return state;
  }
}

function applyQuery(state: PlaceSearchState, query: string): PlaceSearchState {
  const outcome = searchCensusPlaces(query);
  const candidates = candidatesForOutcome(outcome);
  const place_status =
    outcome.kind === "idle"
      ? "PLACE_IDLE"
      : outcome.kind === "unknown"
        ? "PLACE_UNKNOWN"
        : outcome.kind === "ambiguous"
          ? "PLACE_AMBIGUOUS"
          : "PLACE_QUERYING";
  return {
    ...initialPlaceSearchState(),
    route: state.route,
    query,
    place_status,
    candidates,
    fixture_scene: null,
  };
}

function selectPlace(state: PlaceSearchState, place: CensusPlace | null): PlaceSearchState {
  if (!place) {
    return state;
  }
  if (isPhoenixDemoAreaId(place.place_geoid) || isPhoenixDemoAreaId(place.place_name)) {
    return state;
  }
  return {
    ...state,
    query: place.display_name,
    place_status: "PLACE_SELECTED",
    selected_place: place,
    candidates: [place],
    geography_status: "GEO_RESOLVING",
    geography: null,
    unsupported_reason: null,
    unsupported_message: null,
    reference_readiness: "NOT_PREPARED",
    fixture_scene: null,
  };
}

function applyResolved(
  state: PlaceSearchState,
  event: Extract<PlaceSearchEvent, { type: "GEOGRAPHY_RESOLVED" }>,
): PlaceSearchState {
  if (state.geography_status !== "GEO_RESOLVING") {
    return state;
  }
  if (
    state.selected_place &&
    event.geography.place.place_geoid !== state.selected_place.place_geoid
  ) {
    return state;
  }
  if (isPhoenixDemoAreaId(event.geography.area_id)) {
    return state;
  }
  return {
    ...state,
    geography_status: "GEO_READY",
    geography: event.geography,
    unsupported_reason: null,
    unsupported_message: null,
    reference_readiness: "NOT_PREPARED",
  };
}

export function namedUxStates(state: PlaceSearchState): {
  geography: PlaceSearchState["geography_status"];
  reference: PlaceSearchState["reference_readiness"];
  national_phoenix_az: boolean;
  phoenix_demo: boolean;
} {
  return {
    geography: state.geography_status,
    reference: state.reference_readiness,
    national_phoenix_az: state.selected_place
      ? isNationalPhoenixAz(state.selected_place)
      : false,
    phoenix_demo: state.route === "phoenix-demo",
  };
}
