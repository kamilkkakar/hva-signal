import { describe, expect, it } from "vitest";
import {
  ANCHORAGE_AK,
  CHICAGO_IL,
  PHOENIX_AZ_NATIONAL,
  buildResolvedGeography,
  initialPlaceSearchState,
  sceneSnapshot,
} from "../../mocks/placeSearchFixtures";
import { mockResolveGeography } from "./mockResolve";
import {
  namedUxStates,
  productScene,
  reducePlaceSearch,
} from "./stateMachine";
import { PHOENIX_DEMO_AREA_ID, nationalAreaId } from "./types";

describe("place search state machine", () => {
  it("opens on search, not login", () => {
    const state = initialPlaceSearchState();
    expect(productScene(state)).toBe("open_search");
    expect(state.route).toBe("national");
    expect(state.place_status).toBe("PLACE_IDLE");
    expect(state.reference_readiness).toBe("NOT_PREPARED");
  });

  it("keeps a unique typeahead in querying until the user selects", () => {
    const state = reducePlaceSearch(initialPlaceSearchState(), {
      type: "QUERY_CHANGED",
      query: "Chicago, IL",
    });
    expect(state.place_status).toBe("PLACE_QUERYING");
    expect(state.selected_place).toBeNull();
    expect(state.geography_status).toBe("GEO_UNRESOLVED");
    expect(productScene(state)).toBe("open_search");
  });

  it("selecting a place enters resolving and does not imply thermal coverage", () => {
    const state = reducePlaceSearch(initialPlaceSearchState(), {
      type: "SELECT_PLACE",
      place: CHICAGO_IL,
    });
    expect(state.geography_status).toBe("GEO_RESOLVING");
    expect(productScene(state)).toBe("resolving");
    expect(state.reference_readiness).toBe("NOT_PREPARED");
    expect(state.geography).toBeNull();
  });

  it("maps Chicago to a national 25-zone window, never phoenix-demo", () => {
    let state = reducePlaceSearch(initialPlaceSearchState(), {
      type: "SELECT_PLACE",
      place: CHICAGO_IL,
    });
    state = reducePlaceSearch(state, mockResolveGeography(CHICAGO_IL));
    expect(state.geography_status).toBe("GEO_READY");
    expect(state.geography?.area_id).toBe(nationalAreaId("1714000"));
    expect(state.geography?.area_id).not.toBe(PHOENIX_DEMO_AREA_ID);
    expect(state.geography?.expected_zone_count).toBe(25);
    expect(state.geography?.zone_ids).toHaveLength(25);
    expect(state.geography?.reference_readiness).toBe("NOT_PREPARED");
    expect(state.geography?.historical_signal_capable).toBe(false);
    expect(productScene(state)).toBe("analysis_window");
  });

  it("keeps national Phoenix, AZ distinct from phoenix-demo", () => {
    let state = reducePlaceSearch(initialPlaceSearchState(), {
      type: "SELECT_PLACE",
      place: PHOENIX_AZ_NATIONAL,
    });
    state = reducePlaceSearch(state, mockResolveGeography(PHOENIX_AZ_NATIONAL));
    const named = namedUxStates(state);
    expect(named.national_phoenix_az).toBe(true);
    expect(named.phoenix_demo).toBe(false);
    expect(state.geography?.area_id).toBe(nationalAreaId("0455000"));
    expect(state.geography?.area_id).not.toBe(PHOENIX_DEMO_AREA_ID);
    expect(state.reference_readiness).toBe("NOT_PREPARED");
  });

  it("marks Anchorage as unsupported geography, not reference-not-prepared", () => {
    let state = reducePlaceSearch(initialPlaceSearchState(), {
      type: "SELECT_PLACE",
      place: ANCHORAGE_AK,
    });
    state = reducePlaceSearch(state, mockResolveGeography(ANCHORAGE_AK));
    expect(productScene(state)).toBe("unsupported_geography");
    expect(state.geography_status).toBe("GEO_UNSUPPORTED");
    expect(state.unsupported_reason).toBe("UNSUPPORTED_SCOPE");
    expect(state.reference_readiness).toBe("NOT_PREPARED");
  });

  it("refuses to bind phoenix-demo as a resolved national geography", () => {
    let state = reducePlaceSearch(initialPlaceSearchState(), {
      type: "SELECT_PLACE",
      place: CHICAGO_IL,
    });
    const sneaky = buildResolvedGeography(CHICAGO_IL);
    state = reducePlaceSearch(state, {
      type: "GEOGRAPHY_RESOLVED",
      geography: { ...sneaky, area_id: PHOENIX_DEMO_AREA_ID },
    });
    expect(state.geography_status).toBe("GEO_RESOLVING");
    expect(state.geography).toBeNull();
  });

  it("opens the legacy phoenix-demo route without selecting national Phoenix", () => {
    const state = reducePlaceSearch(initialPlaceSearchState(), {
      type: "OPEN_LEGACY_PHOENIX_DEMO",
    });
    expect(state.route).toBe("phoenix-demo");
    expect(state.place_status).toBe("PLACE_LEGACY_PHOENIX_DEMO");
    expect(state.selected_place).toBeNull();
    expect(productScene(state)).toBe("open_search");
  });
});

describe("named fixture scenes", () => {
  it("covers the owned IA states", () => {
    expect(productScene(sceneSnapshot("open_search"))).toBe("open_search");
    expect(productScene(sceneSnapshot("place_ambiguous"))).toBe("place_ambiguous");
    expect(productScene(sceneSnapshot("place_unknown"))).toBe("place_unknown");
    expect(sceneSnapshot("resolving").geography_status).toBe("GEO_RESOLVING");
    expect(productScene(sceneSnapshot("resolving"))).toBe("resolving");
    expect(sceneSnapshot("unsupported_geography").geography_status).toBe(
      "GEO_UNSUPPORTED",
    );
    expect(productScene(sceneSnapshot("unsupported_geography"))).toBe(
      "unsupported_geography",
    );
    expect(sceneSnapshot("place_unknown").query).toBe("Glastonbury, CT");
    expect(
      sceneSnapshot("place_ambiguous").candidates.every(
        (row) => row.place_geoid !== PHOENIX_DEMO_AREA_ID,
      ),
    ).toBe(true);
  });
});
