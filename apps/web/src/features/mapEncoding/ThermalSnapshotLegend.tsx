import {
  THERMAL_C_AXIS,
  THERMAL_C_DENIAL,
  THERMAL_C_HIGH_LABEL,
  THERMAL_C_LOCAL_CONTRAST_NOTE,
  THERMAL_C_LOCAL_CONTRAST_THRESHOLD_C,
  THERMAL_C_LOW_LABEL,
  THERMAL_C_STOPS,
  thermalObservedSpanNote,
} from "./tokens";
import "./legend.css";

export type ThermalSnapshotLegendProps = {
  observedMinC?: number | null;
  observedMaxC?: number | null;
};

export function ThermalSnapshotLegend({
  observedMinC = null,
  observedMaxC = null,
}: ThermalSnapshotLegendProps) {
  const colors = THERMAL_C_STOPS.filter((_, index) => index % 2 === 1) as string[];
  const hasObservedSpan =
    observedMinC != null &&
    observedMaxC != null &&
    Number.isFinite(observedMinC) &&
    Number.isFinite(observedMaxC) &&
    observedMaxC >= observedMinC;
  const spreadC = hasObservedSpan ? observedMaxC - observedMinC : null;
  const localContrast =
    spreadC != null && spreadC > 0 && spreadC < THERMAL_C_LOCAL_CONTRAST_THRESHOLD_C;
  const bandLeft =
    hasObservedSpan && spreadC != null && spreadC > 0
      ? `${((observedMinC - 25) / 20) * 100}%`
      : null;
  const bandWidth =
    hasObservedSpan && spreadC != null && spreadC > 0
      ? `${Math.max((spreadC / 20) * 100, 6)}%`
      : null;

  return (
    <aside
      className="hva-pos-legend hva-thermal-legend"
      aria-label="Selected-time thermal legend"
      data-testid="thermal-snapshot-legend"
      data-local-contrast={localContrast ? "yes" : "no"}
      data-b-public="yes"
    >
      <h3>Selected-time thermal</h3>
      <div className="hva-pos-ramp-block">
        <div
          className="hva-pos-ramp"
          role="img"
          aria-label={`${THERMAL_C_LOW_LABEL} to ${THERMAL_C_HIGH_LABEL}`}
        >
          {colors.map((stop) => (
            <span key={stop} className="hva-pos-stop" style={{ background: stop }} data-stop={stop} />
          ))}
          {bandLeft && bandWidth ? (
            <span
              className="hva-thermal-observed-band"
              aria-hidden="true"
              style={{ left: bandLeft, width: bandWidth }}
            />
          ) : null}
        </div>
        <p className="hva-pos-axis">
          <span>{THERMAL_C_LOW_LABEL}</span>
          <span aria-hidden="true">↔</span>
          <span>{THERMAL_C_HIGH_LABEL}</span>
        </p>
      </div>
      <p className="hva-pos-denial">{THERMAL_C_AXIS}</p>
      <p className="hva-pos-denial">{THERMAL_C_DENIAL}</p>
      {hasObservedSpan ? (
        <p className="hva-pos-hatch-note" data-testid="thermal-observed-span-note">
          {thermalObservedSpanNote(observedMinC, observedMaxC)}
        </p>
      ) : null}
      {localContrast ? (
        <p className="hva-pos-hatch-note" data-testid="thermal-local-contrast-note">
          {THERMAL_C_LOCAL_CONTRAST_NOTE}
        </p>
      ) : null}
      <p className="hva-pos-outline">
        <span className="hva-pos-outline-swatch" style={{ borderColor: "#4e5748" }} aria-hidden="true" />
        Missing zone mean — outline only
      </p>
      <p className="hva-pos-outline">
        <span
          className="hva-pos-outline-swatch"
          style={{ borderColor: "#c45c26", borderWidth: "2px" }}
          aria-hidden="true"
        />
        Selected analysis area
      </p>
    </aside>
  );
}
