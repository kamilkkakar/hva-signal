import type { InteractionCatalog } from "./types";

export type ObservedThermalSpan = {
  minC: number;
  maxC: number;
  spreadC: number;
  zoneCount: number;
};

export function observedThermalSpan(
  catalog: InteractionCatalog | null,
): ObservedThermalSpan | null {
  if (
    !catalog ||
    catalog.fill_kind !== "thermal_absolute" ||
    catalog.kind !== "selected_time_snapshot"
  ) {
    return null;
  }
  const values = catalog.collection.features
    .map((feature) => feature.properties.mean_temperature_c)
    .filter((value): value is number => typeof value === "number" && Number.isFinite(value));
  if (values.length < 2) {
    return null;
  }
  const minC = Math.min(...values);
  const maxC = Math.max(...values);
  return {
    minC,
    maxC,
    spreadC: maxC - minC,
    zoneCount: values.length,
  };
}
