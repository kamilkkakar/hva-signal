import { useEffect, useReducer } from "react";
import { FIXTURE_SCENE_LABELS, initialPlaceSearchState } from "../../mocks/placeSearchFixtures";
import {
  FIXTURE_SWITCHER_LABEL,
  NATIONAL_SEARCH_LABEL,
  NO_COMBINED_SCORE_COPY,
  NOT_THERMAL_PRODUCT_COPY,
  PHOENIX_DEMO_LEGACY_COPY,
  PHOENIX_DEMO_LEGACY_LABEL,
  PRODUCT_EXPANSION,
  PRODUCT_NAME,
} from "./copy";
import { MOCK_RESOLVE_DELAY_MS } from "./mockResolve";
import { resolvePlaceGeography } from "./geographyClient";
import { PlaceSearch } from "./PlaceSearch";
import { ResolutionStage } from "./ResolutionStage";
import { productScene, reducePlaceSearch } from "./stateMachine";
import type { CensusPlace, FixtureSceneId } from "./types";

const SCENE_ORDER = Object.keys(FIXTURE_SCENE_LABELS) as FixtureSceneId[];

export function PlaceSearchShell() {
  const [state, dispatch] = useReducer(
    reducePlaceSearch,
    undefined,
    initialPlaceSearchState,
  );

  useEffect(() => {
    if (state.geography_status !== "GEO_RESOLVING" || !state.selected_place) {
      return;
    }
    const place = state.selected_place;
    let cancelled = false;
    const timer = window.setTimeout(() => {
      void resolvePlaceGeography(place).then((event) => {
        if (!cancelled) {
          dispatch(event);
        }
      });
    }, MOCK_RESOLVE_DELAY_MS);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [state.geography_status, state.selected_place]);

  function onSelect(place: CensusPlace) {
    dispatch({ type: "SELECT_PLACE", place });
  }

  const scene = productScene(state);

  return (
    <div className="shell" data-testid="place-search-shell" data-scene={scene}>
      <header className="shell-banner">
        <div>
          <p className="eyebrow">3K Labs</p>
          <h1>{PRODUCT_NAME}</h1>
          <p className="product-expansion">{PRODUCT_EXPANSION}</p>
        </div>
        <div className="source-cluster">
          <p className="source-banner">{NATIONAL_SEARCH_LABEL}</p>
          <a className="job-id" href="#/phoenix-demo">
            {PHOENIX_DEMO_LEGACY_LABEL}
          </a>
          <p className="copilot-note">{PHOENIX_DEMO_LEGACY_COPY}</p>
        </div>
      </header>

      <div className="shell-grid">
        <PlaceSearch
          state={state}
          onQuery={(query) => dispatch({ type: "QUERY_CHANGED", query })}
          onSelect={onSelect}
          onClear={() => dispatch({ type: "CLEAR_PLACE" })}
        />
        <ResolutionStage state={state} />
        <aside className="decision" aria-label="Independent signals">
          <header className="rail-head">
            <p className="kicker">Signals</p>
            <h2>Not this surface</h2>
          </header>
          <p className="decision-copy">{NOT_THERMAL_PRODUCT_COPY}</p>
          <p className="decision-copy">{NO_COMBINED_SCORE_COPY}</p>
        </aside>
      </div>

      <footer className="timeline" aria-label="IA fixture scenes">
        <p className="kicker">{FIXTURE_SWITCHER_LABEL}</p>
        <ol>
          {SCENE_ORDER.map((id, index) => (
            <li key={id} data-active={state.fixture_scene === id ? "true" : "false"}>
              <button
                type="button"
                className="submit-btn"
                onClick={() => dispatch({ type: "APPLY_SCENE", scene: id })}
              >
                <span className="timeline-index">
                  {String(index + 1).padStart(2, "0")}
                </span>{" "}
                {FIXTURE_SCENE_LABELS[id]}
              </button>
            </li>
          ))}
        </ol>
      </footer>
    </div>
  );
}
