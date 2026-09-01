import {
  CANOPY_STOPS,
  HOUSING_STOPS,
  INCOME_STOPS,
} from "./tokens";
import "./legend.css";

export type ContextModeLegendProps = {
  mode: "TREE_CANOPY" | "INCOME" | "OLDER_HOUSING" | string;
  title: string;
  unit: string;
  sourceLine?: string;
  minLabel?: string;
  maxLabel?: string;
};

function paletteFor(mode: string): { id: string; stops: readonly string[] } {
  if (mode === "TREE_CANOPY" || /canopy|tree/i.test(mode)) {
    return { id: "canopy", stops: CANOPY_STOPS };
  }
  if (mode === "INCOME" || /income/i.test(mode)) {
    return { id: "income", stops: INCOME_STOPS };
  }
  return { id: "housing", stops: HOUSING_STOPS };
}

export function ContextModeLegend({
  mode,
  title,
  unit,
  sourceLine,
  minLabel = "Lower",
  maxLabel = "Higher",
}: ContextModeLegendProps) {
  const palette = paletteFor(mode);
  return (
    <aside
      className="hva-pos-legend hva-context-legend"
      aria-label={`${title} legend`}
      data-testid="context-mode-legend"
      data-mode={mode}
      data-palette={palette.id}
      data-unit={unit}
      data-relative-scale="displayed-geography"
    >
      <h3>{title}</h3>
      <div className="hva-pos-ramp-block">
        <div className="hva-pos-ramp" role="img" aria-label={`${minLabel} to ${maxLabel}`}>
          {palette.stops.map((stop) => (
            <span key={stop} className="hva-pos-stop" style={{ background: stop }} data-stop={stop} />
          ))}
        </div>
        <p className="hva-pos-axis">
          <span>{minLabel}</span>
          <span aria-hidden="true">↔</span>
          <span>{maxLabel}</span>
        </p>
      </div>
      <p className="hva-pos-denial" data-testid="context-legend-unit">
        {unit}
      </p>
      <p className="hva-pos-hatch-note" data-testid="context-relative-scale-note">
        Relative within the displayed comparison geography; not a risk score.
      </p>
      <p className="hva-pos-outline">
        <span className="hva-pos-outline-swatch" style={{ borderColor: "#4e5748" }} aria-hidden="true" />
        Missing
      </p>
      <p className="hva-pos-outline">
        <span
          className="hva-pos-outline-swatch"
          style={{ borderColor: "#c45c26", borderWidth: "2px" }}
          aria-hidden="true"
        />
        Selected area
      </p>
      <details className="hva-legend-about">
        <summary>About this layer</summary>
        {sourceLine ? <p className="hva-pos-hatch-note">{sourceLine}</p> : null}
      </details>
    </aside>
  );
}
