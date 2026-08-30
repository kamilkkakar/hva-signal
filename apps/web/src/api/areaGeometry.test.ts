import { describe, expect, it, vi } from "vitest";
import { createGeometryLoader, fetchAreaGeometry } from "./areaGeometry";

const collection = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      properties: { GEOID: "04013107401" },
      geometry: { type: "Polygon", coordinates: [] },
    },
  ],
};

function geometryResponse(overrides?: { area?: string; version?: string; sha?: string }) {
  return new Response(JSON.stringify(collection), {
    status: 200,
    headers: {
      "Content-Type": "application/geo+json",
      "X-HVA-Area-ID": overrides?.area ?? "phoenix-demo",
      "X-HVA-Zone-Geometry-Version":
        overrides?.version ??
        "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f",
      "X-HVA-Geometry-SHA256":
        overrides?.sha ??
        "3f16870fc801da5052b03e0f09c172feb4a1e0d6736452d22ffd6f09bb4e11f0",
    },
  });
}

describe("fetchAreaGeometry", () => {
  it("requests the same-origin versioned geometry path for the current area_id", async () => {
    const fetchImpl = vi.fn(async () => geometryResponse()) as unknown as typeof fetch;
    const payload = await fetchAreaGeometry("phoenix-demo", fetchImpl);
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    const [url, init] = fetchImpl.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/areas/phoenix-demo/geometry");
    expect(url.startsWith("/api/")).toBe(true);
    expect(url).not.toMatch(/onrender\.com/);
    expect(init.method).toBe("GET");
    expect(payload.areaId).toBe("phoenix-demo");
    expect(payload.zoneGeometryVersion).toBe(
      "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f",
    );
    expect(payload.geometrySha256).toBe(
      "3f16870fc801da5052b03e0f09c172feb4a1e0d6736452d22ffd6f09bb4e11f0",
    );
    expect(payload.collection.type).toBe("FeatureCollection");
    expect(payload.collection.features).toHaveLength(1);
  });

  it("rejects a geometry HTTP failure without a static fallback", async () => {
    const fetchImpl = vi.fn(async () => new Response("missing", { status: 404 })) as unknown as typeof fetch;
    await expect(fetchAreaGeometry("not-a-supported-area", fetchImpl)).rejects.toThrow(
      /geometry/i,
    );
    expect(fetchImpl.mock.calls[0]?.[0]).toBe(
      "/api/v1/areas/not-a-supported-area/geometry",
    );
  });

  it("recovers identity from the area catalog when CORS hides geometry headers", async () => {
    const fetchImpl = vi.fn(async (url: string) => {
      if (String(url).endsWith("/api/v1/areas")) {
        return new Response(
          JSON.stringify({
            areas: [
              {
                area_id: "phoenix-demo",
                zone_geometry_version:
                  "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f",
              },
            ],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return new Response(JSON.stringify(collection), {
        status: 200,
        headers: { "Content-Type": "application/geo+json" },
      });
    }) as unknown as typeof fetch;
    const payload = await fetchAreaGeometry("phoenix-demo", fetchImpl);
    expect(payload.areaId).toBe("phoenix-demo");
    expect(payload.zoneGeometryVersion).toBe(
      "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f",
    );
    expect(payload.collection.features).toHaveLength(1);
  });

  it("rejects a non-FeatureCollection body", async () => {
    const fetchImpl = vi.fn(
      async () =>
        new Response(JSON.stringify({ type: "Point", coordinates: [0, 0] }), {
          status: 200,
          headers: {
            "X-HVA-Area-ID": "phoenix-demo",
            "X-HVA-Zone-Geometry-Version": "v",
            "X-HVA-Geometry-SHA256": "abc",
          },
        }),
    ) as unknown as typeof fetch;
    await expect(fetchAreaGeometry("phoenix-demo", fetchImpl)).rejects.toThrow(/GeoJSON/i);
  });
});

describe("createGeometryLoader", () => {
  it("does not let a stale geometry response overwrite a newer area", async () => {
    let releaseSlow: (() => void) | undefined;
    const slow = new Promise<void>((resolve) => {
      releaseSlow = resolve;
    });
    const fetchImpl = vi.fn(async (url: string) => {
      if (String(url).includes("old-area")) {
        await slow;
        return geometryResponse({ area: "old-area" });
      }
      return geometryResponse({ area: "phoenix-demo" });
    }) as unknown as typeof fetch;

    const loader = createGeometryLoader(fetchImpl);
    const first = loader.load("old-area");
    const second = loader.load("phoenix-demo");
    releaseSlow?.();
    const stale = await first;
    const fresh = await second;
    expect(stale.stale).toBe(true);
    expect(fresh.stale).toBe(false);
    if (!fresh.stale) {
      expect(fresh.payload.areaId).toBe("phoenix-demo");
    }
  });
});
