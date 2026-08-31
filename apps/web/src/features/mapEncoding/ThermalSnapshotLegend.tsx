import {
  THERMAL_C_AXIS,
  THERMAL_C_DENIAL,
  THERMAL_C_HIGH_LABEL,
  THERMAL_C_LOW_LABEL,
  THERMAL_C_NARROW_NOTE,
  THERMAL_C_STOPS,
} from "./tokens";
import "./legend.css";

export type ThermalSnapshotLegendProps = {
  narrowRange?: boolean;
};

export function ThermalSnapshotLegend({ narrowRange = false }: ThermalSnapshotLegendProps) {
  const colors = THERMAL_C_STOPS.filter((_, index) => index % 2 === 1) as string[];
  return (
    <aside
      className="hva-pos-legend hva-thermal-legend"
      aria-label="Selected-time thermal legend"
      data-testid="thermal-snapshot-legend"
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
        </div>
        <p className="hva-pos-axis">
          <span>{THERMAL_C_LOW_LABEL}</span>
          <span aria-hidden="true">↔</span>
          <span>{THERMAL_C_HIGH_LABEL}</span>
        </p>
      </div>
      <p className="hva-pos-denial">{THERMAL_C_AXIS}</p>
      <p className="hva-pos-denial">{THERMAL_C_DENIAL}</p>
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
      {narrowRange ? <p className="hva-pos-hatch-note">{THERMAL_C_NARROW_NOTE}</p> : null}
    </aside>
  );
}
