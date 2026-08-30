import { formatSignalBTemperatureC } from "./signalBPolicy";
import type {
  SignalBBoundFeature,
  SignalBSnapshot,
  SignalBTableRow,
} from "./signalBTypes";

function rowFromParts(
  zoneId: string,
  mean: number | null,
  coverage: string,
): SignalBTableRow {
  const missing = coverage === "missing" || mean == null || !Number.isFinite(mean);
  const value = missing ? null : mean;
  return {
    zone_id: zoneId,
    mean_temperature_c: value,
    display_temperature: formatSignalBTemperatureC(value),
    coverage_status: missing ? (coverage === "missing" ? coverage : "missing") : coverage,
    units: "celsius",
  };
}

/** Table is first-class V1 chrome. Sort key is zone_id, never temperature. */
export function signalBTableRows(input: {
  snapshot: SignalBSnapshot;
  boundFeatures?: SignalBBoundFeature[];
}): SignalBTableRow[] {
  const rows = new Map<string, SignalBTableRow>();
  for (const feature of input.boundFeatures ?? []) {
    rows.set(
      feature.properties.zone_id,
      rowFromParts(
        feature.properties.zone_id,
        feature.properties.mean_temperature_c,
        feature.properties.coverage_status,
      ),
    );
  }
  for (const zone of input.snapshot.zones) {
    if (!rows.has(zone.zone_id)) {
      rows.set(
        zone.zone_id,
        rowFromParts(zone.zone_id, zone.mean_temperature_c, zone.coverage_status),
      );
    }
  }
  return [...rows.values()].sort((left, right) => left.zone_id.localeCompare(right.zone_id));
}
