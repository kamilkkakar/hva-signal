import {
  B1_B3_DISCLOSURE,
  GEO_CHIP_GEOGRAPHY_READY,
  GEO_CHIP_REFERENCE_NOT_PREPARED,
  GEOGRAPHY_REFERENCE_SPLIT_COPY,
  NOT_THERMAL_PRODUCT_COPY,
  OPEN_SEARCH_STAGE_COPY,
  RESOLVING_COPY,
  UNSUPPORTED_GEOGRAPHY_COPY,
} from "./copy";
import type { PlaceSearchState } from "./types";

type ResolutionStageProps = {
  state: PlaceSearchState;
};

export function ResolutionStage({ state }: ResolutionStageProps) {
  const place = state.selected_place;
  const ready = state.geography_status === "GEO_READY" ? state.geography : null;

  return (
    <main
      className="map-stage"
      aria-label="Analysis geography"
      data-testid="resolution-stage"
      data-geo-state={state.geography_status}
    >
      <div className="fiducial fiducial-nw" aria-hidden="true" />
      <div className="fiducial fiducial-ne" aria-hidden="true" />
      <div className="fiducial fiducial-sw" aria-hidden="true" />
      <div className="fiducial fiducial-se" aria-hidden="true" />

      <div className="map-overlay">
        {place && ready && (
          <>
            <p className="map-label" data-testid="display-label">
              {ready.display_label}
            </p>
            <p className="map-hover" data-testid="analysis-window-caption">
              {ready.analysis_window_caption}
            </p>
          </>
        )}

        {state.geography_status === "GEO_UNRESOLVED" && (
          <p className="map-empty">{OPEN_SEARCH_STAGE_COPY}</p>
        )}
        {state.geography_status === "GEO_RESOLVING" && (
          <p className="map-empty" data-testid="resolving-copy">
            {RESOLVING_COPY}
          </p>
        )}
        {(state.geography_status === "GEO_UNSUPPORTED" ||
          state.geography_status === "GEO_FAILED") && (
          <p className="map-limitation" data-testid="unsupported-copy">
            {state.unsupported_message ?? UNSUPPORTED_GEOGRAPHY_COPY}
          </p>
        )}
        {ready && (
          <>
            <p className="evidence-stamp" data-testid="geo-chip-ready">
              {GEO_CHIP_GEOGRAPHY_READY}
            </p>
            <p className="evidence-stamp" data-testid="geo-chip-reference">
              {GEO_CHIP_REFERENCE_NOT_PREPARED}
            </p>
            <p className="copilot-note">{GEOGRAPHY_REFERENCE_SPLIT_COPY}</p>
            <p className="copilot-note">{NOT_THERMAL_PRODUCT_COPY}</p>
            <p className="copilot-note">{B1_B3_DISCLOSURE}</p>
            <p className="job-id">area_id {ready.area_id}</p>
          </>
        )}
        <p className="map-coords" aria-hidden="true">
          FIXTURE GEOGRAPHY · NO TILESERVER · NO THERMAL COVERAGE
        </p>
      </div>
    </main>
  );
}
