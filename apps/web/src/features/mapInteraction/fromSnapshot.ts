import { buildCatalog } from "./catalog";
import {
  formatMeanC,
  formatTimeLabel,
  productSourceLabel,
  zoneLabel,
} from "./policy";
import type { InteractionCatalog, InteractionCollection, InteractionZone } from "./types";
import { emptyStoryFields, formatObservationLabel } from "./zoneStory";

export type SnapshotZoneInput = {
  zone_id: string;
  mean_temperature_c: number | null;
  coverage_status: string;
};

export type SnapshotFeatureInput = {
  properties?: Record<string, unknown> | null;
  geometry?: unknown;
};

export function catalogFromSnapshot(input: {
  zones: SnapshotZoneInput[];
  geometry?: { features: SnapshotFeatureInput[] } | null;
  targetTimestamp?: string | null;
  timezone?: string | null;
  source?: string | null;
  dataStatus?: string | null;
}): InteractionCatalog {
  const time_label = formatTimeLabel(input.targetTimestamp, input.timezone);
  const source_label = productSourceLabel(input.dataStatus ?? input.source);
  const geomById = new Map<string, SnapshotFeatureInput>();
  for (const feature of input.geometry?.features ?? []) {
    const props = feature.properties ?? {};
    const id =
      props.zone_id != null
        ? String(props.zone_id)
        : props.GEOID != null
          ? String(props.GEOID)
          : null;
    if (id) {
      geomById.set(id, feature);
    }
  }

  const zones: InteractionZone[] = [];
  const collection: InteractionCollection = { type: "FeatureCollection", features: [] };

  for (const zone of input.zones) {
    const missing =
      zone.coverage_status === "missing" ||
      zone.mean_temperature_c == null ||
      !Number.isFinite(zone.mean_temperature_c);
    const value = missing ? null : zone.mean_temperature_c;
    const coverage = missing ? "missing" : "valid";
    const feature = geomById.get(zone.zone_id);
    const displayName =
      typeof feature?.properties?.display_name === "string"
        ? String(feature.properties.display_name)
        : null;
    zones.push({
      geoid: zone.zone_id,
      zone_id: zone.zone_id,
      label: zoneLabel(zone.zone_id, displayName),
      value_display: formatMeanC(value),
      value_kind: "mean_c",
      coverage,
      time_label,
      source_label,
      has_semantic_fill: !missing,
      ...emptyStoryFields({
        observation_label: formatObservationLabel(input.targetTimestamp),
        source_label,
      }),
    });
    collection.features.push({
      type: "Feature",
      geometry: feature?.geometry ?? null,
      properties: {
        ...(feature?.properties ?? {}),
        GEOID: zone.zone_id,
        zone_id: zone.zone_id,
        mean_temperature_c: value,
        has_semantic_fill: !missing,
        value_display: formatMeanC(value),
        coverage,
        time_label,
        source_label,
      },
    });
  }

  return buildCatalog({
    kind: "selected_time_snapshot",
    zones,
    collection,
    time_label,
    source_label,
    fill_authorized: true,
    fill_kind: "thermal_absolute",
    layer_title: "Selected-time thermal conditions",
    meaning: input.targetTimestamp
      ? `Zone-mean TCM · °C · ${formatObservationLabel(input.targetTimestamp)}`
      : "Zone-mean TCM · °C",
  });
}
