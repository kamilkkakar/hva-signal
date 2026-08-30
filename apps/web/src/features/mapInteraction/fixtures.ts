import { catalogFromHistorical } from "./fromHistorical";
import { catalogFromSnapshot } from "./fromSnapshot";
import type { InteractionCatalog } from "./types";

export const FIXTURE_ZONE_IDS = [
  "FIX-0455000-01",
  "FIX-0455000-02",
  "FIX-0455000-03",
  "FIX-0455000-04",
  "FIX-0455000-05",
] as const;

function cellPolygon(index: number): { type: "Polygon"; coordinates: number[][][] } {
  const x0 = index;
  return {
    type: "Polygon",
    coordinates: [
      [
        [x0, 0],
        [x0 + 1, 0],
        [x0 + 1, 1],
        [x0, 1],
        [x0, 0],
      ],
    ],
  };
}

/** Schematic locator cells. Not TIGER and not product-map truth. */
export function fixtureGeometry() {
  return {
    type: "FeatureCollection" as const,
    features: FIXTURE_ZONE_IDS.map((zoneId, index) => ({
      type: "Feature" as const,
      properties: { GEOID: zoneId, zone_id: zoneId },
      geometry: cellPolygon(index),
    })),
  };
}

export function snapshotCatalog(partial = false): InteractionCatalog {
  const zones = FIXTURE_ZONE_IDS.map((zone_id, index) => ({
    zone_id,
    mean_temperature_c: partial && index === 4 ? null : 39.9 + index * 0.1,
    coverage_status: partial && index === 4 ? "missing" : "valid",
  }));
  return catalogFromSnapshot({
    zones,
    geometry: fixtureGeometry(),
    targetTimestamp: "2024-07-15T15:00:00",
    timezone: "America/Phoenix",
    source: "replay",
    dataStatus: "replay",
  });
}

export function historicalCatalog(authorized: boolean): InteractionCatalog {
  const features = FIXTURE_ZONE_IDS.map((zoneId, index) => ({
    properties: {
      GEOID: zoneId,
      zone_id: zoneId,
      q_A: authorized ? 0.2 + index * 0.1 : 0.2 + index * 0.1,
      backend_order: authorized ? index + 1 : index + 1,
      thermal_ordering_permitted: authorized,
      display_name: `Locator ${index + 1}`,
    },
    geometry: cellPolygon(index),
  }));
  return catalogFromHistorical({
    features,
    analysisTime: "2024-07-15T10:00:00.000Z",
    timezone: "America/Phoenix",
    thermalSource: "replay",
    dataStatus: "replay",
    dataMode: "replay",
    fillAuthorized: authorized,
  });
}

export function emptyInteractionCatalog(): InteractionCatalog {
  return catalogFromSnapshot({
    zones: [],
    geometry: { features: [] },
    source: null,
  });
}
