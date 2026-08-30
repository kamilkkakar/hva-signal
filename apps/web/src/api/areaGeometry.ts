import { apiUrl } from "./baseUrl";

export type AreaGeometryCollection = {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    properties: Record<string, unknown> | null;
    geometry: unknown;
  }>;
};

export type AreaGeometryPayload = {
  areaId: string;
  zoneGeometryVersion: string;
  geometrySha256: string;
  collection: AreaGeometryCollection;
};

export type GeometryLoadResult =
  | { stale: true }
  | { stale: false; payload: AreaGeometryPayload };

type AreaSummary = {
  area_id?: string;
  zone_geometry_version?: string;
};

function header(response: Response, name: string): string {
  return response.headers.get(name)?.trim() ?? "";
}

function isFeatureCollection(body: unknown): body is AreaGeometryCollection {
  return (
    !!body &&
    typeof body === "object" &&
    (body as { type?: unknown }).type === "FeatureCollection" &&
    Array.isArray((body as { features?: unknown }).features)
  );
}

async function resolveIdentityFromCatalog(
  areaId: string,
  fetchImpl: typeof fetch,
): Promise<{ areaId: string; zoneGeometryVersion: string }> {
  const response = await fetchImpl(apiUrl("/api/v1/areas"), {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Area catalog could not be loaded (${response.status}).`);
  }
  const body = (await response.json()) as { areas?: AreaSummary[] };
  const match = (body.areas ?? []).find((row) => row.area_id === areaId);
  if (!match?.zone_geometry_version) {
    throw new Error(`Area catalog has no geometry version for ${areaId}.`);
  }
  return { areaId, zoneGeometryVersion: match.zone_geometry_version };
}

export async function fetchAreaGeometry(
  areaId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<AreaGeometryPayload> {
  const response = await fetchImpl(
    apiUrl(`/api/v1/areas/${encodeURIComponent(areaId)}/geometry`),
    {
      method: "GET",
      headers: { Accept: "application/geo+json, application/json" },
    },
  );
  if (!response.ok) {
    throw new Error(`Area geometry could not be loaded (${response.status}).`);
  }
  const body: unknown = await response.json();
  if (!isFeatureCollection(body)) {
    throw new Error("Geometry response is not a GeoJSON FeatureCollection.");
  }
  let resolvedAreaId = header(response, "X-HVA-Area-ID");
  let zoneGeometryVersion = header(response, "X-HVA-Zone-Geometry-Version");
  let geometrySha256 = header(response, "X-HVA-Geometry-SHA256");
  if (!resolvedAreaId || !zoneGeometryVersion) {
    const catalog = await resolveIdentityFromCatalog(areaId, fetchImpl);
    resolvedAreaId = resolvedAreaId || catalog.areaId;
    zoneGeometryVersion = zoneGeometryVersion || catalog.zoneGeometryVersion;
  }
  if (!resolvedAreaId || !zoneGeometryVersion) {
    throw new Error("Geometry response is missing identity headers.");
  }
  return {
    areaId: resolvedAreaId,
    zoneGeometryVersion,
    geometrySha256: geometrySha256 || "unexposed",
    collection: body,
  };
}

export function createGeometryLoader(fetchImpl: typeof fetch = fetch) {
  let generation = 0;
  return {
    invalidate() {
      generation += 1;
    },
    async load(areaId: string): Promise<GeometryLoadResult> {
      const current = ++generation;
      const payload = await fetchAreaGeometry(areaId, fetchImpl);
      if (current !== generation) {
        return { stale: true };
      }
      return { stale: false, payload };
    },
  };
}
