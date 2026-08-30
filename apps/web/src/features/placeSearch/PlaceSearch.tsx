import {
  AMBIGUOUS_PLACE_COPY,
  SEARCH_HINT,
  SEARCH_LABEL,
  SEARCH_PLACEHOLDER,
  UNKNOWN_PLACE_COPY,
} from "./copy";
import type { CensusPlace, PlaceSearchState } from "./types";

type PlaceSearchProps = {
  state: PlaceSearchState;
  onQuery: (query: string) => void;
  onSelect: (place: CensusPlace) => void;
  onClear: () => void;
};

export function PlaceSearch({
  state,
  onQuery,
  onSelect,
  onClear,
}: PlaceSearchProps) {
  const showList =
    state.candidates.length > 0 && state.geography_status !== "GEO_RESOLVING";

  return (
    <aside className="rail" aria-label="Census Place search">
      <header className="rail-head">
        <p className="kicker">Place</p>
        <h2>Search Census Place</h2>
      </header>
      <div className="query-form">
        <label>
          {SEARCH_LABEL}
          <input
            name="place_query"
            value={state.query}
            onChange={(event) => onQuery(event.target.value)}
            placeholder={SEARCH_PLACEHOLDER}
            autoComplete="off"
            spellCheck={false}
            data-testid="place-search"
          />
        </label>
      </div>
      <p className="copilot-note">{SEARCH_HINT}</p>
      {state.place_status === "PLACE_UNKNOWN" && (
        <p className="form-error" role="status" data-testid="place-unknown">
          {UNKNOWN_PLACE_COPY}
        </p>
      )}
      {state.place_status === "PLACE_AMBIGUOUS" && (
        <p className="copilot-note" data-testid="place-ambiguous">
          {AMBIGUOUS_PLACE_COPY}
        </p>
      )}
      {showList && (
        <ul className="query-form" data-testid="place-candidates" style={{ listStyle: "none", padding: 0 }}>
          {state.candidates.map((place) => {
            const selected = state.selected_place?.place_geoid === place.place_geoid;
            return (
              <li key={place.place_geoid}>
                <button
                  type="button"
                  className="submit-btn"
                  data-selected={selected ? "true" : "false"}
                  onClick={() => onSelect(place)}
                >
                  <span>{place.display_name}</span>
                  <span className="job-id">
                    {place.official_name} · GEOID {place.place_geoid} · {place.place_type}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
      {state.selected_place && (
        <button type="button" className="submit-btn" onClick={onClear}>
          Clear place
        </button>
      )}
    </aside>
  );
}
