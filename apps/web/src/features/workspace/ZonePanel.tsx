import type { StoryAction } from "./actionEngine";
import { HvaStoryRail, type HvaStage } from "./HvaStoryRail";
import { OutlookPanel } from "./OutlookPanel";
import type { ZoneInfo } from "./types";

type SpatialState = {
  supported: boolean;
  label: string;
  sentence: string;
  loading?: boolean;
};

type ZonePanelProps = {
  zone: ZoneInfo | null;
  rangeLabel: string | null;
  spatialState: SpatialState | null;
  actions: readonly StoryAction[];
  highlights: readonly string[];
  stage: HvaStage;
  onStageChange: (stage: HvaStage) => void;
  hasLocalAnalysis?: boolean;
  forecastSupported?: boolean;
};

function formatC(value: number | null): string {
  if (value == null) return "\u2014";
  return `${value.toFixed(1)}\u00a0\u00b0C`;
}

export function ZonePanel({
  zone,
  rangeLabel,
  spatialState,
  actions,
  highlights,
  stage,
  onStageChange,
  hasLocalAnalysis,
  forecastSupported = false,
}: ZonePanelProps) {
  if (!zone) {
    return (
      <aside className="ws-zone-panel" data-testid="zone-panel" aria-label="Zone details">
        <HvaStoryRail stage={stage} onStageChange={onStageChange} />
        <p className="ws-zone-empty">Select a zone on the map</p>
      </aside>
    );
  }

  return (
    <aside className="ws-zone-panel" data-testid="zone-panel" aria-label="Zone details">
      <HvaStoryRail stage={stage} onStageChange={onStageChange} />

      <div className="ws-zone-header">
        <h2 className="ws-zone-name" data-testid="zone-name">
          Zone {zone.label.replace(/^Census Tract\s*/, "")}
        </h2>
        {zone.secondaryLabel ? (
          <p className="ws-zone-secondary" data-testid="zone-secondary">{zone.secondaryLabel}</p>
        ) : null}
      </div>

      {(stage === "heat" || stage === "context") && (
        <dl className="ws-zone-metrics" data-testid="hva-heat-metrics">
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
          {zone.olderHousingPct != null ? (
            <div className="ws-metric-row">
              <dt>Older housing</dt>
              <dd>{zone.olderHousingPct.toFixed(0)}%</dd>
            </div>
          ) : null}
        </dl>
      )}

      {stage === "heat" && spatialState ? (
        <div
          className="ws-spatial-gate"
          data-supported={spatialState.supported ? "true" : "false"}
          data-loading={spatialState.loading ? "true" : "false"}
          data-testid="spatial-gate"
        >
          <p className="ws-gate-label">{spatialState.label}</p>
          <p className="ws-gate-sentence">{spatialState.sentence}</p>
        </div>
      ) : null}

      {stage === "context" ? (
        <div className="ws-context-highlights" data-testid="hva-context-highlights">
          <p className="ws-control-label">What changes the picture</p>
          {highlights.length > 0 ? (
            <ul>
              {highlights.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          ) : (
            <p className="ws-gate-sentence">
              Context values stay visible without above/below calls when uncertainty policy
              suppresses comparison.
            </p>
          )}
        </div>
      ) : null}

      {stage === "action" && actions.length > 0 ? (
        <nav className="ws-next-actions" data-testid="next-actions" aria-label="Next actions">
          <p className="ws-control-label">What should we do next</p>
          <ul>
            {actions.slice(0, 3).map((action, index) => (
              <li key={action.id} data-action-id={action.id}>
                <span>{action.label}</span>
                <span className="ws-action-why" data-testid={`action-why-${index}`}>
                  {action.whyShown}
                </span>
              </li>
            ))}
          </ul>
        </nav>
      ) : null}

      {stage === "outlook" ? <OutlookPanel forecastSupported={forecastSupported} /> : null}

      <details className="ws-methods-disclosure" data-testid="zone-methods">
        <summary>Methods &amp; provenance</summary>
        <p>
          {hasLocalAnalysis
            ? "FortyGuard Type-1 TCM · 100 m resolution · cached observation."
            : "Comparison-mode context uses published cross-city metrics for the selected observation only."}{" "}
          Census Tract geography from US Census Bureau TIGER/Line 2025. Context from ACS 5-year
          estimates and NLCD 2021.
        </p>
      </details>
    </aside>
  );
}
