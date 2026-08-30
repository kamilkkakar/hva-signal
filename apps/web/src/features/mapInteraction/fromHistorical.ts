import { buildCatalog } from "./catalog";
import {
  formatQuantile,
  formatTimeLabel,
  productSourceLabel,
  zoneLabel,
} from "./policy";
import type { InteractionCatalog, InteractionCollection, InteractionZone } from "./types";

export type HistoricalFeatureInput = {
  properties?: Record<string, unknown> | null;
  geometry?: unknown;
};

/**
 * Bind already-joined historical features. Fill authorization is an input.
 * This adapter does not compute rank or read system-limitation layer labels.
 */
export function catalogFromHistorical(input: {
  features: HistoricalFeatureInput[];
  analysisTime?: string | null;
  timezone?: string | null;
  thermalSource?: string | null;
  dataStatus?: string | null;
  dataMode?: string | null;
  fillAuthorized: boolean;
}): InteractionCatalog {
  const time_label = formatTimeLabel(input.analysisTime, input.timezone);
  const source_label = productSourceLabel(
    input.dataStatus ?? input.dataMode ?? input.thermalSource,
  );
  const zones: InteractionZone[] = [];
  const collection: InteractionCollection = { type: "FeatureCollection", features: [] };

  for (const feature of input.features) {
    const props = feature.properties ?? {};
    const geoid = props.GEOID != null ? String(props.GEOID) : props.zone_id != null
      ? String(props.zone_id)
      : null;
    if (!geoid) {
      continue;
    }
    const rawQ = props.q_A;
    const qA = typeof rawQ === "number" && Number.isFinite(rawQ) ? rawQ : null;
    const permitted = props.thermal_ordering_permitted === true;
    const coverage =
      qA != null && permitted
        ? "valid"
        : permitted
          ? "missing"
          : "not authorized";
    const hasFill = input.fillAuthorized && permitted && qA != null;
    const displayName = typeof props.display_name === "string" ? props.display_name : null;
    zones.push({
      geoid,
      zone_id: props.zone_id != null ? String(props.zone_id) : geoid,
      label: zoneLabel(geoid, displayName),
      value_display: formatQuantile(qA),
      value_kind: "q_A",
      coverage,
      time_label,
      source_label,
      has_semantic_fill: hasFill,
    });
    collection.features.push({
      type: "Feature",
      geometry: feature.geometry ?? null,
      properties: {
        ...props,
        GEOID: geoid,
        zone_id: props.zone_id != null ? String(props.zone_id) : geoid,
        has_semantic_fill: hasFill,
        value_display: formatQuantile(qA),
        coverage,
        time_label,
        source_label,
      },
    });
  }

  return buildCatalog({
    kind: input.fillAuthorized ? "historical_ordering" : "aoi_outline",
    zones,
    collection,
    time_label,
    source_label,
    fill_authorized: input.fillAuthorized,
  });
}
