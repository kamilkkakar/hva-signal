import {
  THERMAL_C_AXIS,
  THERMAL_C_DENIAL,
  THERMAL_C_HIGH_LABEL,
  THERMAL_C_LOW_LABEL,
  THERMAL_C_NARROW_NOTE,
  thermalObservedSpanNote,
} from "./tokens";
import {
  ACTIVE_THERMAL_DISPLAY_SCALE,
  thermalObservedBandPosition,
  thermalScaleTickLabels,
} from "./thermalDisplayScale";
import "./legend.css";

export type ThermalSnapshotLegendProps = {
  observedMinC?: number | null;
  observedMaxC?: number | null;
  /** Deprecated compatibility props. Selected-time °C can no longer be AOI-stretched. */
  enhanceLocalContrast?: boolean;
  onEnhanceLocalContrastChange?: (next: boolean) => void;
  /** Optional override; defaults to ACTIVE_THERMAL_DISPLAY_SCALE. */
  scale?: typeof ACTIVE_THERMAL_DISPLAY_SCALE;
};

export function ThermalSnapshotLegend({
  observedMinC = null,
  observedMaxC = null,
  scale = ACTIVE_THERMAL_DISPLAY_SCALE,
}: ThermalSnapshotLegendProps) {
  const colors = scale.stops.filter((_, index) => index % 2 === 1) as string[];
  const tickLabels = thermalScaleTickLabels(scale);
  const hasObservedSpan =
    observedMinC != null &&
    observedMaxC != null &&
    Number.isFinite(observedMinC) &&
    Number.isFinite(observedMaxC) &&
    observedMaxC >= observedMinC;
  const spreadC = hasObservedSpan ? observedMaxC - observedMinC : null;
  const lowVariation = spreadC != null && spreadC > 0 && spreadC < 2;
  const band =
    hasObservedSpan && spreadC != null && spreadC > 0
      ? thermalObservedBandPosition(observedMinC, observedMaxC, scale)
      : null;

  return (
    <aside
      className="hva-pos-legend hva-thermal-legend"
      aria-label="Selected-time thermal legend"
      data-testid="thermal-snapshot-legend"
      data-local-contrast="no"
      data-fixed-scale="yes"
      data-scale-version={scale.version}
      data-scale-min={scale.domainMin}
      data-scale-max={scale.domainMax}
      data-b-public="yes"
    >
      <h3>Selected-time thermal conditions</h3>
      <div className="hva-pos-ramp-block">
        <div
          className="hva-pos-ramp"
          role="img"
          aria-label={`${THERMAL_C_LOW_LABEL} to ${THERMAL_C_HIGH_LABEL}`}
          style={{ gridTemplateColumns: `repeat(${colors.length}, minmax(0, 1fr))` }}
        >
          {colors.map((stop) => (
            <span key={stop} className="hva-pos-stop" style={{ background: stop }} data-stop={stop} />
          ))}
          {band ? (
            <span
              className="hva-thermal-observed-band"
              aria-hidden="true"
              style={{ left: `${band.leftPct}%`, width: `${band.widthPct}%` }}
            />
          ) : null}
        </div>
        <ol
          className="hva-thermal-ticks"
          data-testid="thermal-legend-ticks"
          aria-label={`Temperature scale in ${scale.unit}`}
        >
          {tickLabels.map((label, index) => (
            <li key={`${label}-${index}`} data-tick={scale.ticks[index]}>
              <span className="hva-thermal-tick-value">{label}</span>
              {index === tickLabels.length - 1 ? (
                <span className="hva-thermal-tick-unit">{scale.unit}</span>
              ) : null}
            </li>
          ))}
        </ol>
      </div>
      <p className="hva-pos-denial">{THERMAL_C_AXIS}</p>
      {hasObservedSpan ? (
        <p className="hva-pos-hatch-note" data-testid="thermal-observed-span-note">
          {thermalObservedSpanNote(observedMinC, observedMaxC)}
        </p>
      ) : null}
      {lowVariation ? (
        <p className="hva-pos-hatch-note" data-testid="thermal-low-variation">
          Low spatial variation. {THERMAL_C_NARROW_NOTE}
        </p>
      ) : null}
      <details className="hva-legend-about">
        <summary>About this layer</summary>
        <p className="hva-pos-denial">{THERMAL_C_DENIAL}</p>
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
      </details>
    </aside>
  );
}
