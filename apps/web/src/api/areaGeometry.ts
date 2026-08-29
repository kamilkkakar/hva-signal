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

function header(response: Response, name: string): string {
  const value = response.headers.get(name)?.trim() ?? "";
  if (!value) {
    throw new Error(`Geometry response is missing ${name}.`);
  }
  return value;
}

export async function fetchAreaGeometry(
  areaId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<AreaGeometryPayload> {
  const response = await fetchImpl(
    `/api/v1/areas/${encodeURIComponent(areaId)}/geometry`,
    {
      method: "GET",
      headers: { Accept: "application/geo+json, application/json" },
    },
  );
  if (!response.ok) {
    throw new Error(`Area geometry could not be loaded (${response.status}).`);
  }
  const body: unknown = await response.json();
  if (
    !body ||
    typeof body !== "object" ||
    (body as { type?: unknown }).type !== "FeatureCollection" ||
    !Array.isArray((body as { features?: unknown }).features)
  ) {
    throw new Error("Geometry response is not a GeoJSON FeatureCollection.");
  }
  return {
    areaId: header(response, "X-HVA-Area-ID"),
    zoneGeometryVersion: header(response, "X-HVA-Zone-Geometry-Version"),
    geometrySha256: header(response, "X-HVA-Geometry-SHA256"),
    collection: body as AreaGeometryCollection,
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
