import {
  ContextModeLegend,
  HistoricalPositionLegend,
  ThermalSnapshotLegend,
} from "@/features/mapEncoding";
import {
  CLEAR_LAYER_LABEL,
  CLEAR_SELECTION_LABEL,
  FIT_AOI_LABEL,
  LIST_CAPTION,
  LIST_SUMMARY,
  MAP_ADVANCED_SUMMARY,
  MAP_TOOLS_SUMMARY,
  POSITION_MEANING,
  QA_EXPAND_LABEL,
  RESET_AOI_LABEL,
  RESTORE_LAYER_LABEL,
  SELECT_PROMPT,
  TABLE_CAPTION,
} from "./policy";
import type { InteractionEvent, MapInteractionView } from "./types";

export type MapInteractionChromeProps = {
  view: MapInteractionView;
  dispatch: (event: InteractionEvent) => void;
  catalogKind?: string | null;
  fillKind?: string | null;
  layerTitle?: string | null;
  layerMeaning?: string | null;
  observedMinC?: number | null;
  observedMaxC?: number | null;
  enhanceLocalContrast?: boolean;
  onEnhanceLocalContrastChange?: (next: boolean) => void;
};

function contextModeFromTitle(title: string, meaning: string): {
  mode: string;
  unit: string;
  sourceLine: string;
} {
  const blob = `${title} ${meaning}`.toLowerCase();
  if (blob.includes("canopy") || blob.includes("tree")) {
    return {
      mode: "TREE_CANOPY",
      unit: "% of plantable ground",
      sourceLine: meaning || "Phoenix shade study · tree canopy",
    };
  }
  if (blob.includes("income")) {
    return {
      mode: "INCOME",
      unit: "USD · ACS 2020–2024",
      sourceLine: meaning || "ACS 5-year median household income",
    };
  }
  return {
    mode: "OLDER_HOUSING",
    unit: "% homes built before 1980",
    sourceLine: meaning || "ACS 5-year older housing share",
  };
}

export function MapInteractionChrome({
  view,
  dispatch,
  catalogKind: _catalogKind = null,
  fillKind = null,
  layerTitle = null,
  layerMeaning = null,
  observedMinC = null,
  observedMaxC = null,
  enhanceLocalContrast = false,
  onEnhanceLocalContrastChange,
}: MapInteractionChromeProps) {
  void _catalogKind;
  const contextMeta =
    fillKind === "context_quantity"
      ? contextModeFromTitle(layerTitle ?? view.layerTitle, layerMeaning ?? view.meaningCopy)
      : null;

  return (
    <div className="mapi-chrome" data-testid="map-interaction-chrome">
      <section className="mapi-legend" aria-label="Map legend" data-testid="map-interaction-legend">
        <h3>Legend</h3>
        {fillKind === "thermal_absolute" ? (
          <ThermalSnapshotLegend
            observedMinC={observedMinC}
            observedMaxC={observedMaxC}
            enhanceLocalContrast={enhanceLocalContrast}
            onEnhanceLocalContrastChange={onEnhanceLocalContrastChange}
          />
        ) : fillKind === "context_quantity" && contextMeta ? (
          <ContextModeLegend
            mode={contextMeta.mode}
            title={layerTitle ?? view.layerTitle}
            unit={contextMeta.unit}
            sourceLine={contextMeta.sourceLine}
          />
        ) : view.positionLegendMode === "sufficient" ||
          view.positionLegendMode === "insufficient" ? (
          <HistoricalPositionLegend mode={view.positionLegendMode} />
        ) : (
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
        )}
      </section>

      <p className="mapi-sr" aria-live="polite" data-testid="map-interaction-announce">
        {view.announce}
      </p>

      <details className="mapi-advanced" data-testid="map-advanced-chrome">
        <summary>{MAP_ADVANCED_SUMMARY}</summary>

        <details className="mapi-tools" data-testid="map-tools">
          <summary>{MAP_TOOLS_SUMMARY}</summary>
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
        </details>

        <section
          className="mapi-detail"
          aria-label="Zone details"
          data-testid="map-interaction-detail"
          data-has-selection={view.detail ? "true" : "false"}
          data-position-shown={view.detail?.position_shown ? "true" : "false"}
        >
          <h3>Zone details</h3>
          {view.detail ? (
            <>
              <p className="mapi-zone-id" data-testid="detail-zone-heading">
                Selected analysis zone
              </p>
              {view.detail.position_shown && view.detail.position_pct != null ? (
                <div
                  className="mapi-position"
                  data-testid="detail-position-visual"
                  aria-label="Nighttime historical position"
                >
                  <p className="mapi-position-kicker">Nighttime historical position</p>
                  <div className="mapi-position-track" aria-hidden="true">
                    <span
                      className="mapi-position-mark"
                      style={{ left: `${view.detail.position_pct}%` }}
                    />
                  </div>
                </div>
              ) : null}
              <dl>
                <dt>Position</dt>
                <dd data-testid="detail-position-meaning">{view.detail.position_meaning}</dd>
                <dt>Observation</dt>
                <dd data-testid="detail-observation">{view.detail.observation_label}</dd>
                <dt>Source</dt>
                <dd data-testid="detail-source-story">{view.detail.source_story}</dd>
                {view.detail.relative_order_line ? (
                  <>
                    <dt>Within analysis</dt>
                    <dd data-testid="detail-relative-order">{view.detail.relative_order_line}</dd>
                  </>
                ) : null}
                <dt className="mapi-sr">GEOID</dt>
                <dd className="mapi-sr" data-testid="detail-geoid">
                  {view.detail.geoid}
                </dd>
                <dt className="mapi-sr">Label</dt>
                <dd className="mapi-sr" data-testid="detail-label">
                  {view.detail.label}
                </dd>
                <dt className="mapi-sr">Value</dt>
                <dd className="mapi-sr" data-testid="detail-value">
                  {view.detail.value_display}
                </dd>
                <dt className="mapi-sr">Coverage</dt>
                <dd className="mapi-sr" data-testid="detail-coverage">
                  {view.detail.coverage}
                </dd>
                <dt className="mapi-sr">Time</dt>
                <dd className="mapi-sr" data-testid="detail-time">
                  {view.detail.time_label}
                </dd>
                <dt className="mapi-sr">Source token</dt>
                <dd className="mapi-sr" data-testid="detail-source">
                  {view.detail.source_label}
                </dd>
              </dl>
              {view.detail.q_A_display ? (
                <details className="mapi-qa" data-testid="detail-qa">
                  <summary>{QA_EXPAND_LABEL}</summary>
                  <p data-testid="detail-qa-value">
                    q_A = {view.detail.q_A_display}
                  </p>
                </details>
              ) : null}
              <p className="mapi-copy mapi-position-note">{POSITION_MEANING}</p>
            </>
          ) : (
            <p className="mapi-copy">{view.layerActive ? SELECT_PROMPT : view.meaningCopy}</p>
          )}
        </section>

        <details
          className="mapi-list-wrap"
          aria-label="Zone identifiers"
          data-testid="map-interaction-list-wrap"
        >
          <summary>{LIST_SUMMARY}</summary>
          <p className="mapi-copy">{LIST_CAPTION}</p>
          <ul className="mapi-zone-list" data-testid="map-interaction-list">
            {view.tableRows.map((row) => {
              const selected = view.selectedId === row.geoid;
              return (
                <li key={row.geoid} data-geoid={row.geoid} data-selected={selected ? "true" : "false"}>
                  <button
                    type="button"
                    aria-pressed={selected}
                    onClick={() => dispatch({ type: "select", geoid: row.geoid })}
                  >
                    {row.label}
                  </button>
                  <span>{row.value_display}</span>
                </li>
              );
            })}
          </ul>
        </details>

        <details className="mapi-table-wrap" aria-label="Zone table">
          <summary>All zones (table)</summary>
          <p className="mapi-copy">{TABLE_CAPTION}</p>
          <table className="mapi-table" data-testid="map-interaction-table">
            <caption className="mapi-sr">{TABLE_CAPTION}</caption>
            <thead>
              <tr>
                <th>Zone</th>
                <th>Label</th>
                <th>Position</th>
                <th>Coverage</th>
                <th>Observation</th>
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
        </details>
      </details>
    </div>
  );
}
