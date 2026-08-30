import { formatSignalBTemperatureC } from "./signalBPolicy";
import type {
  SignalBBoundCollection,
  SignalBBoundFeature,
  SignalBGeometryCollection,
  SignalBSnapshot,
  SignalBSnapshotZone,
} from "./signalBTypes";

export type SignalBBindSuccess = {
  ok: true;
  collection: SignalBBoundCollection;
  joinedCount: number;
  missingTemperatureCount: number;
};

export type SignalBBindFailure = {
  ok: false;
  reason: string;
};

export type SignalBBindResult = SignalBBindSuccess | SignalBBindFailure;

function featureZoneId(
  feature: SignalBGeometryCollection["features"][number],
): string | null {
  const props = feature.properties ?? {};
  if (props.zone_id != null) {
    return String(props.zone_id);
  }
  if (props.GEOID != null) {
    return String(props.GEOID);
  }
  return null;
}

function zoneIsValid(zone: SignalBSnapshotZone | undefined): boolean {
  if (!zone) {
    return false;
  }
  if (zone.coverage_status === "missing") {
    return false;
  }
  return zone.mean_temperature_c != null && Number.isFinite(zone.mean_temperature_c);
}

export function bindSignalBGeometry(input: {
  geometry: SignalBGeometryCollection;
  snapshot: SignalBSnapshot;
}): SignalBBindResult {
  const zoneById = new Map<string, SignalBSnapshotZone>();
  for (const zone of input.snapshot.zones) {
    if (zoneById.has(zone.zone_id)) {
      return { ok: false, reason: "Snapshot zones contain duplicate zone identifiers." };
    }
    zoneById.set(zone.zone_id, zone);
  }

  const seen = new Set<string>();
  const features: SignalBBoundFeature[] = [];
  for (const feature of input.geometry.features) {
    const zoneId = featureZoneId(feature);
    if (!zoneId) {
      return { ok: false, reason: "Geometry feature is missing zone_id or GEOID." };
    }
    if (seen.has(zoneId)) {
      return { ok: false, reason: "Geometry contains duplicate zone identifiers." };
    }
    seen.add(zoneId);
    const zone = zoneById.get(zoneId);
    const valid = zoneIsValid(zone);
    const mean = valid ? (zone?.mean_temperature_c ?? null) : null;
    features.push({
      type: "Feature",
      geometry: feature.geometry,
      properties: {
        GEOID: zoneId,
        zone_id: zoneId,
        mean_temperature_c: mean,
        coverage_status: zone?.coverage_status ?? "missing",
        display_temperature: formatSignalBTemperatureC(mean),
        has_valid_temperature: valid,
        units: "celsius",
        aggregation_method: "centroid_within_mean",
      },
    });
  }

  return {
    ok: true,
    collection: { type: "FeatureCollection", features },
    joinedCount: features.length,
    missingTemperatureCount: features.filter((item) => !item.properties.has_valid_temperature)
      .length,
  };
}

export function featureCollectionBounds(
  collection: { features: Array<{ geometry: unknown }> },
): [[number, number], [number, number]] | null {
  let minLng = Infinity;
  let minLat = Infinity;
  let maxLng = -Infinity;
  let maxLat = -Infinity;
  const visit = (value: unknown): void => {
    if (!Array.isArray(value)) {
      return;
    }
    if (
      value.length >= 2 &&
      typeof value[0] === "number" &&
      typeof value[1] === "number"
    ) {
      minLng = Math.min(minLng, value[0]);
      maxLng = Math.max(maxLng, value[0]);
      minLat = Math.min(minLat, value[1]);
      maxLat = Math.max(maxLat, value[1]);
      return;
    }
    for (const item of value) {
      visit(item);
    }
  };
  for (const feature of collection.features) {
    visit((feature.geometry as { coordinates?: unknown } | null)?.coordinates);
  }
  if (!Number.isFinite(minLng) || !Number.isFinite(minLat)) {
    return null;
  }
  return [
    [minLng, minLat],
    [maxLng, maxLat],
  ];
}
