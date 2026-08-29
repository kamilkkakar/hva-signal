import type { AreaGeometryCollection, AreaGeometryPayload } from "@/api/areaGeometry";
import type { AnalysisResultStub, ZoneDecisionStub } from "@/api/analysisJobs";

export const GEOMETRY_ZONE_ID_PROPERTY = "GEOID";

export type PresentationFeature = {
  type: "Feature";
  properties: Record<string, unknown> & {
    GEOID: string;
    zone_id: string;
    backend_order: number;
    thermal_ordering_permitted: boolean;
    ranked: boolean;
    q_A: number | null;
  };
  geometry: unknown;
};

export type PresentationCollection = {
  type: "FeatureCollection";
  features: PresentationFeature[];
};

export type GeometryBindSuccess = {
  ok: true;
  featureCount: number;
  joinedCount: number;
  missingAnalysisGeoids: string[];
  extraGeometryGeoids: string[];
  collection: PresentationCollection;
};

export type GeometryBindFailure = {
  ok: false;
  reason: string;
  rankedFillCount: 0;
};

export type GeometryBindResult = GeometryBindSuccess | GeometryBindFailure;

function featureGeoid(feature: AreaGeometryCollection["features"][number]): string | null {
  const value = feature.properties?.[GEOMETRY_ZONE_ID_PROPERTY];
  if (value == null) {
    return null;
  }
  return String(value);
}

function resultGeometryVersion(result: AnalysisResultStub): string | null {
  return result.versions?.zone_geometry_version ?? null;
}

export function bindGeometryToAnalysis(input: {
  geometry: AreaGeometryPayload;
  requestAreaId: string;
  result: AnalysisResultStub;
}): GeometryBindResult {
  if (input.geometry.areaId !== input.requestAreaId) {
    return {
      ok: false,
      reason: `Geometry area_id ${input.geometry.areaId} does not match analysis area ${input.requestAreaId}.`,
      rankedFillCount: 0,
    };
  }
  const resultVersion = resultGeometryVersion(input.result);
  if (!resultVersion || resultVersion !== input.geometry.zoneGeometryVersion) {
    return {
      ok: false,
      reason: "Geometry version does not match this analysis result.",
      rankedFillCount: 0,
    };
  }
  const zones = input.result.zones ?? [];
  const zoneById = new Map<string, { zone: ZoneDecisionStub; order: number }>();
  for (const [index, zone] of zones.entries()) {
    if (zoneById.has(zone.zone_id)) {
      return {
        ok: false,
        reason: "Analysis zones contain duplicate zone identifiers.",
        rankedFillCount: 0,
      };
    }
    zoneById.set(zone.zone_id, { zone, order: index + 1 });
  }
  const geometryIds: string[] = [];
  const seen = new Set<string>();
  for (const feature of input.geometry.collection.features) {
    const geoid = featureGeoid(feature);
    if (!geoid) {
      return {
        ok: false,
        reason: `Geometry feature is missing ${GEOMETRY_ZONE_ID_PROPERTY}.`,
        rankedFillCount: 0,
      };
    }
    if (seen.has(geoid)) {
      return {
        ok: false,
        reason: "Geometry contains duplicate GEOID values.",
        rankedFillCount: 0,
      };
    }
    seen.add(geoid);
    geometryIds.push(geoid);
  }
  const analysisIds = [...zoneById.keys()];
  const extraGeometryGeoids = geometryIds.filter((id) => !zoneById.has(id));
  const missingAnalysisGeoids = analysisIds.filter((id) => !seen.has(id));
  if (
    missingAnalysisGeoids.length > 0 ||
    extraGeometryGeoids.length > 0 ||
    geometryIds.length !== analysisIds.length
  ) {
    return {
      ok: false,
      reason: "Geometry GEOIDs do not match analysis zone identifiers.",
      rankedFillCount: 0,
    };
  }
  const features: PresentationFeature[] = input.geometry.collection.features.map(
    (feature) => {
      const geoid = featureGeoid(feature) as string;
      const matched = zoneById.get(geoid);
      if (!matched) {
        throw new Error("join invariant violated");
      }
      return {
        type: "Feature",
        geometry: feature.geometry,
        properties: {
          ...(feature.properties ?? {}),
          GEOID: geoid,
          zone_id: matched.zone.zone_id,
          backend_order: matched.order,
          thermal_ordering_permitted: matched.zone.thermal_ordering_permitted === true,
          ranked: matched.zone.ranked === true,
          q_A: typeof matched.zone.q_A === "number" ? matched.zone.q_A : null,
        },
      };
    },
  );
  return {
    ok: true,
    featureCount: features.length,
    joinedCount: features.length,
    missingAnalysisGeoids: [],
    extraGeometryGeoids: [],
    collection: { type: "FeatureCollection", features },
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
