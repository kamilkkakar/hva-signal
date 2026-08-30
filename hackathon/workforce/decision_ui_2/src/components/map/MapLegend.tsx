import type { MapModeModel } from "@/contracts";

type MapLegendProps = {
  readonly mode: MapModeModel;
};

export function MapLegend({ mode }: MapLegendProps) {
  return (
    <aside className="legend" aria-label="Map legend" data-testid="map-legend">
      <h3>{mode.title}</h3>
      <dl className="meta-row">
        <div>
          <dt>Unit</dt>
          <dd>{mode.unit}</dd>
        </div>
        <div>
          <dt>Period</dt>
          <dd>{mode.period}</dd>
        </div>
        <div>
          <dt>Baseline</dt>
          <dd>{mode.baseline}</dd>
        </div>
      </dl>
      <ul>
        {mode.legend.map((stop) => (
          <li key={stop.id}>
            <span
              className="swatch"
              style={stop.swatch ? { background: stop.swatch } : undefined}
            />
            <span>{stop.label}</span>
          </li>
        ))}
      </ul>
    </aside>
  );
}
