import { historicalPositionLegend, type LegendMode } from "./legend";
import "./legend.css";

export type HistoricalPositionLegendProps = {
  mode: LegendMode;
};

export function HistoricalPositionLegend({ mode }: HistoricalPositionLegendProps) {
  const view = historicalPositionLegend(mode);
  return (
    <aside
      className="hva-pos-legend"
      aria-label="Historical position legend"
      data-testid="historical-position-legend"
      data-legend-mode={view.mode}
      data-b-public="no"
    >
      <h3>{view.title}</h3>
      {view.stops.length > 0 && view.lowLabel && view.highLabel ? (
        <div className="hva-pos-ramp-block">
          <div
            className="hva-pos-ramp"
            role="img"
            aria-label={view.axis ?? `${view.lowLabel} to ${view.highLabel}`}
          >
            {view.stops.map((stop) => (
              <span
                key={stop}
                className="hva-pos-stop"
                style={{ background: stop }}
                data-stop={stop}
              />
            ))}
          </div>
          <p className="hva-pos-axis">
            <span>{view.lowLabel}</span>
            <span aria-hidden="true">↔</span>
            <span>{view.highLabel}</span>
          </p>
        </div>
      ) : null}
      {view.hatchSamples.length > 0 ? (
        <ul className="hva-pos-hatch">
          {view.hatchSamples.map((sample) => (
            <li key={sample.id}>
              <span className={`hva-pos-hatch-swatch hva-pos-hatch-swatch--${sample.id}`} />
              {sample.label}
            </li>
          ))}
        </ul>
      ) : null}
      {view.outlineSwatch ? (
        <p className="hva-pos-outline">
          <span
            className="hva-pos-outline-swatch"
            style={{ borderColor: view.outlineSwatch }}
            aria-hidden="true"
          />
          Geography outline
        </p>
      ) : null}
      <p className="hva-pos-denial">{view.denial}</p>
      {view.hatchNote ? <p className="hva-pos-hatch-note">{view.hatchNote}</p> : null}
    </aside>
  );
}
