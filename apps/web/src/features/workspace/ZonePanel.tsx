import type { ZoneInfo } from "./types";

type SpatialState = {
  supported: boolean;
  label: string;
  sentence: string;
};

type ZonePanelProps = {
  zone: ZoneInfo | null;
  rangeLabel: string | null;
  spatialState: SpatialState | null;
  nextActions: readonly string[];
  phoenixDeep?: boolean;
};

function formatC(value: number | null): string {
  if (value == null) return "\u2014";
  return `${value.toFixed(1)}\u00a0\u00b0C`;
}

export function ZonePanel({
  zone,
  rangeLabel,
  spatialState,
  nextActions,
  phoenixDeep,
}: ZonePanelProps) {
  if (!zone) {
    return (
      <aside className="ws-zone-panel" data-testid="zone-panel" aria-label="Zone details">
        <p className="ws-zone-empty">Select a zone on the map</p>
      </aside>
    );
  }

  return (
    <aside className="ws-zone-panel" data-testid="zone-panel" aria-label="Zone details">
      <div className="ws-zone-header">
        <h2 className="ws-zone-name" data-testid="zone-name">
          Zone {zone.label.replace(/^Census Tract\s*/, "")}
        </h2>
        {zone.secondaryLabel ? (
          <p className="ws-zone-secondary" data-testid="zone-secondary">{zone.secondaryLabel}</p>
        ) : null}
      </div>

      <dl className="ws-zone-metrics">
        <div className="ws-metric-row ws-metric-primary">
          <dt>Temperature</dt>
          <dd data-testid="zone-temp">{formatC(zone.temperatureC)}</dd>
        </div>
        {rangeLabel ? (
          <div className="ws-metric-row">
            <dt>City range</dt>
            <dd data-testid="zone-range">{rangeLabel}</dd>
          </div>
        ) : null}
        {zone.canopyPct != null ? (
          <div className="ws-metric-row">
            <dt>Tree canopy</dt>
            <dd>{zone.canopyPct.toFixed(0)}%</dd>
          </div>
        ) : null}
        {zone.incomeUsd != null ? (
          <div className="ws-metric-row">
            <dt>Income</dt>
            <dd>${zone.incomeUsd.toLocaleString()}</dd>
          </div>
        ) : null}
      </dl>

      {spatialState ? (
        <div
          className="ws-spatial-gate"
          data-supported={spatialState.supported ? "true" : "false"}
          data-testid="spatial-gate"
        >
          <p className="ws-gate-label">{spatialState.label}</p>
          <p className="ws-gate-sentence">{spatialState.sentence}</p>
        </div>
      ) : null}

      {nextActions.length > 0 ? (
        <nav className="ws-next-actions" data-testid="next-actions" aria-label="Next actions">
          <p className="ws-control-label">Next</p>
          <ul>
            {nextActions.slice(0, 3).map((action) => (
              <li key={action}>{action}</li>
            ))}
          </ul>
        </nav>
      ) : null}

      {phoenixDeep ? (
        <details className="ws-methods-disclosure" data-testid="zone-methods">
          <summary>Methods &amp; provenance</summary>
          <p>
            FortyGuard Type-1 TCM · 100 m resolution · cached observation.
            Census Tract geography from US Census Bureau TIGER/Line 2025.
            Context from ACS 5-year estimates and NLCD 2021.
          </p>
        </details>
      ) : null}
    </aside>
  );
}
