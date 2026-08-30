import { formatSignalBTemperatureC } from "./signalBPolicy";
import type { SignalBHover } from "./signalBTypes";

export function signalBHoverFromProperties(
  properties: Record<string, unknown> | null | undefined,
): SignalBHover | null {
  if (!properties || properties.zone_id == null) {
    return null;
  }
  const rawMean = properties.mean_temperature_c;
  const mean =
    typeof rawMean === "number" && Number.isFinite(rawMean) ? rawMean : null;
  return {
    zone_id: String(properties.zone_id),
    display_temperature: formatSignalBTemperatureC(mean),
    coverage_status:
      typeof properties.coverage_status === "string"
        ? properties.coverage_status
        : mean == null
          ? "missing"
          : "valid",
    units: "celsius",
    aggregation_method: "centroid_within_mean",
  };
}
