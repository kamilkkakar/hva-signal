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

type GeometryLoaderOptions = {
  attempts?: number;
  retryDelayMs?: number;
  sleep?: (delayMs: number) => Promise<void>;
};

class AreaGeometryHttpError extends Error {
  constructor(readonly status: number) {
    super(`Area geometry could not be loaded (${status}).`);
  }
}

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
    throw new AreaGeometryHttpError(response.status);
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

export function createGeometryLoader(
  fetchImpl: typeof fetch = fetch,
  options: GeometryLoaderOptions = {},
) {
  let generation = 0;
  const attempts = Math.max(1, options.attempts ?? 10);
  const retryDelayMs = Math.max(0, options.retryDelayMs ?? 500);
  const sleep = options.sleep ?? ((delayMs: number) => new Promise<void>((resolve) => {
    window.setTimeout(resolve, delayMs);
  }));
  return {
    invalidate() {
      generation += 1;
    },
    async load(areaId: string): Promise<GeometryLoadResult> {
      const current = ++generation;
      for (let attempt = 1; attempt <= attempts; attempt += 1) {
        try {
          const payload = await fetchAreaGeometry(areaId, fetchImpl);
          if (current !== generation) {
            return { stale: true };
          }
          return { stale: false, payload };
        } catch (error) {
          if (current !== generation) {
            return { stale: true };
          }
          const retryable =
            !(error instanceof AreaGeometryHttpError) ||
            error.status === 429 ||
            error.status >= 500;
          if (!retryable || attempt === attempts) {
            throw error;
          }
          await sleep(retryDelayMs * attempt);
        }
      }
      throw new Error("Area geometry retry loop ended unexpectedly.");
    },
  };
}
