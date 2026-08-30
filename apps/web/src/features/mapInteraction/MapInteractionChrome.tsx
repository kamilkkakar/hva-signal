import {
  CLEAR_LAYER_LABEL,
  CLEAR_SELECTION_LABEL,
  FIT_AOI_LABEL,
  RESET_AOI_LABEL,
  RESTORE_LAYER_LABEL,
  SELECT_PROMPT,
  TABLE_CAPTION,
} from "./policy";
import type { InteractionEvent, MapInteractionView } from "./types";

export type MapInteractionChromeProps = {
  view: MapInteractionView;
  dispatch: (event: InteractionEvent) => void;
};

export function MapInteractionChrome({ view, dispatch }: MapInteractionChromeProps) {
  return (
    <div className="mapi-chrome" data-testid="map-interaction-chrome">
      <p className="mapi-label" data-testid="map-interaction-chrome-title">
        {view.layerTitle}
      </p>
      <div className="mapi-toolbar" role="toolbar" aria-label="Map interaction">
        <button
          type="button"
          data-testid="map-fit-aoi"
          disabled={!view.canFitAoi}
          onClick={() => dispatch({ type: "fit_aoi" })}
        >
          {FIT_AOI_LABEL}
        </button>
        <button
          type="button"
          data-testid="map-reset-aoi"
          disabled={!view.canFitAoi}
          onClick={() => dispatch({ type: "reset_aoi" })}
        >
          {RESET_AOI_LABEL}
        </button>
        {view.canRestoreLayer ? (
          <button
            type="button"
            data-testid="map-restore-layer"
            onClick={() => dispatch({ type: "restore_layer" })}
          >
            {RESTORE_LAYER_LABEL}
          </button>
        ) : (
          <button
            type="button"
            data-testid="map-clear-layer"
            disabled={!view.canClearLayer}
            onClick={() => dispatch({ type: "clear_layer" })}
          >
            {CLEAR_LAYER_LABEL}
          </button>
        )}
        <button
          type="button"
          data-testid="map-clear-selection"
          disabled={!view.selectedId}
          onClick={() => dispatch({ type: "clear_selection" })}
        >
          {CLEAR_SELECTION_LABEL}
        </button>
      </div>

      <p className="mapi-sr" aria-live="polite" data-testid="map-interaction-announce">
        {view.announce}
      </p>

      <section className="mapi-legend" aria-label="Map legend" data-testid="map-interaction-legend">
        <h3>Legend</h3>
        <ul>
          {view.legend.map((item) => (
            <li key={item.id}>
              <span
                className="mapi-swatch"
                data-empty={item.swatch ? "false" : "true"}
                style={item.swatch ? { background: item.swatch } : undefined}
                aria-hidden="true"
              />
              <span>
                <strong>{item.label}</strong>
                {" — "}
                {item.meaning}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section
        className="mapi-detail"
        aria-label="Selected zone"
        data-testid="map-interaction-detail"
        data-has-selection={view.detail ? "true" : "false"}
      >
        <h3>Selected zone</h3>
        {view.detail ? (
          <dl>
            <dt>GEOID</dt>
            <dd data-testid="detail-geoid">{view.detail.geoid}</dd>
            <dt>Label</dt>
            <dd data-testid="detail-label">{view.detail.label}</dd>
            <dt>Value</dt>
            <dd data-testid="detail-value">{view.detail.value_display}</dd>
            <dt>Coverage</dt>
            <dd data-testid="detail-coverage">{view.detail.coverage}</dd>
            <dt>Time</dt>
            <dd data-testid="detail-time">{view.detail.time_label}</dd>
            <dt>Source</dt>
            <dd data-testid="detail-source">{view.detail.source_label}</dd>
          </dl>
        ) : (
          <p className="mapi-copy">{view.layerActive ? SELECT_PROMPT : view.meaningCopy}</p>
        )}
      </section>

      <section className="mapi-table-wrap" aria-label="Zone list">
        <h3>Zones</h3>
        <p className="mapi-copy">{TABLE_CAPTION}</p>
        <table className="mapi-table" data-testid="map-interaction-table">
          <caption className="mapi-sr">{TABLE_CAPTION}</caption>
          <thead>
            <tr>
              <th>GEOID</th>
              <th>Label</th>
              <th>Value</th>
              <th>Coverage</th>
              <th>Time</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {view.tableRows.map((row) => {
              const selected = view.selectedId === row.geoid;
              return (
                <tr key={row.geoid} data-geoid={row.geoid} data-selected={selected ? "true" : "false"}>
                  <td>
                    <button
                      type="button"
                      aria-pressed={selected}
                      onClick={() => dispatch({ type: "select", geoid: row.geoid })}
                    >
                      {row.geoid}
                    </button>
                  </td>
                  <td>{row.label}</td>
                  <td>{row.value_display}</td>
                  <td>{row.coverage}</td>
                  <td>{row.time_label}</td>
                  <td>{row.source_label}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </div>
  );
}
