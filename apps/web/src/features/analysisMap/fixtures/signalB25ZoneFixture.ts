import type { SignalBGeometryCollection, SignalBSnapshot } from "../signalBTypes";

export const SIGNAL_B_FIXTURE_ZONE_COUNT = 25;
export const SIGNAL_B_FIXTURE_PLACE_GEOID = "0455000";

/** Schematic 5×5 locator cells. Not TIGER and not product-map truth. */
export function signalBFixtureZoneIds(
  placeGeoid = SIGNAL_B_FIXTURE_PLACE_GEOID,
): string[] {
  return Array.from({ length: SIGNAL_B_FIXTURE_ZONE_COUNT }, (_, index) => {
    const n = String(index + 1).padStart(2, "0");
    return `FIX-${placeGeoid}-${n}`;
  });
}

function linearSeries(min: number, max: number, count: number): number[] {
  if (count <= 1) {
    return [min];
  }
  const step = (max - min) / (count - 1);
  return Array.from({ length: count }, (_, index) => min + step * index);
}

function cellPolygon(index: number): { type: "Polygon"; coordinates: number[][][] } {
  const col = index % 5;
  const row = Math.floor(index / 5);
  const x0 = col;
  const y0 = 4 - row;
  return {
    type: "Polygon",
    coordinates: [
      [
        [x0, y0],
        [x0 + 1, y0],
        [x0 + 1, y0 + 1],
        [x0, y0 + 1],
        [x0, y0],
      ],
    ],
  };
}

export function signalBFixtureGeometry(
  placeGeoid = SIGNAL_B_FIXTURE_PLACE_GEOID,
): SignalBGeometryCollection {
  return {
    type: "FeatureCollection",
    features: signalBFixtureZoneIds(placeGeoid).map((zoneId, index) => ({
      type: "Feature",
      properties: { zone_id: zoneId, GEOID: zoneId },
      geometry: cellPolygon(index),
    })),
  };
}

function snapshotFromMeans(
  means: Array<number | null>,
  extras: Partial<SignalBSnapshot> = {},
  placeGeoid = SIGNAL_B_FIXTURE_PLACE_GEOID,
): SignalBSnapshot {
  const ids = signalBFixtureZoneIds(placeGeoid);
  const zones = ids.map((zone_id, index) => {
    const mean = means[index] ?? null;
    return {
      zone_id,
      mean_temperature_c: mean,
      tile_count: mean == null ? 0 : 4,
      coverage_status: mean == null ? "missing" : "valid",
    };
  });
  const valid = zones
    .map((zone) => zone.mean_temperature_c)
    .filter((value): value is number => value != null);
  return {
    units: "celsius",
    aggregation_method: "centroid_within_mean",
    spatial_resolution: "zone",
    user_facing_tile_map: false,
    target_timestamp: extras.target_timestamp,
    timezone: extras.timezone ?? "America/Phoenix",
    zones,
    expected_zone_count: SIGNAL_B_FIXTURE_ZONE_COUNT,
    valid_zone_count: valid.length,
    missing_zone_ids: zones
      .filter((zone) => zone.coverage_status === "missing")
      .map((zone) => zone.zone_id),
    temperature_min_c: valid.length ? Math.min(...valid) : null,
    temperature_max_c: valid.length ? Math.max(...valid) : null,
    ...extras,
  };
}

/** Illustrative 0.200 °C afternoon field. Not a contrast threshold. */
export function afternoonFlatSnapshot(): SignalBSnapshot {
  return snapshotFromMeans(linearSeries(39.946, 40.146, SIGNAL_B_FIXTURE_ZONE_COUNT), {
    target_timestamp: "2024-07-15T15:00:00",
  });
}

/** Illustrative ~3 °C night field. Fill stays the same as the flat scene. */
export function nightStructuredSnapshot(): SignalBSnapshot {
  return snapshotFromMeans(linearSeries(30.023, 33.02, SIGNAL_B_FIXTURE_ZONE_COUNT), {
    target_timestamp: "2024-07-15T03:00:00",
  });
}

export function afternoonPartialSnapshot(): SignalBSnapshot {
  const means: Array<number | null> = linearSeries(
    39.946,
    40.146,
    SIGNAL_B_FIXTURE_ZONE_COUNT,
  );
  means[24] = null;
  return snapshotFromMeans(means, {
    target_timestamp: "2024-07-15T15:00:00",
  });
}
