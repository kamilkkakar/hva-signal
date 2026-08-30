import { buildCatalog } from "./catalog";
import {
  MISSING_DISPLAY,
  formatNighttimeOrder,
  formatTimeLabel,
  productSourceLabel,
  zoneLabel,
} from "./policy";
import type { InteractionCatalog, InteractionCollection, InteractionZone } from "./types";

export type HistoricalFeatureInput = {
  properties?: Record<string, unknown> | null;
  geometry?: unknown;
};

function finiteNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function orderDenominator(features: HistoricalFeatureInput[]): number {
  let count = 0;
  for (const feature of features) {
    if (finiteNumber(feature.properties?.backend_order) != null) {
      count += 1;
    }
  }
  return count;
}

/**
 * Bind already-joined historical features. Fill authorization is an input.
 * Chrome shows backend nighttime order, never q_A. This adapter does not
 * compute rank or read system-limitation layer labels.
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
  const of = orderDenominator(input.features);
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
    const order = finiteNumber(props.backend_order);
    const permitted = props.thermal_ordering_permitted === true;
    const coverage = !input.fillAuthorized
      ? "order withheld"
      : order != null && permitted
        ? "valid"
        : permitted
          ? "missing"
          : "not authorized";
    const hasFill = input.fillAuthorized && permitted && order != null;
    const displayName = typeof props.display_name === "string" ? props.display_name : null;
    const value_display = hasFill ? formatNighttimeOrder(order, of) : MISSING_DISPLAY;
    zones.push({
      geoid,
      zone_id: props.zone_id != null ? String(props.zone_id) : geoid,
      label: zoneLabel(geoid, displayName),
      value_display,
      value_kind: hasFill ? "order" : "none",
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
        value_display,
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
