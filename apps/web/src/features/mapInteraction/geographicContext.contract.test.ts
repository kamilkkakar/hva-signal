import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  path.join(__dirname, "MapInteractionStage.tsx"),
  "utf8",
);

describe("geographic map context contract", () => {
  it("uses a neutral no-key vector basemap with visible attribution", () => {
    expect(source).toContain("https://tiles.openfreemap.org/styles/positron");
    expect(source).toContain("attributionControl: { compact: true }");
    expect(source).not.toContain("basemaps.cartocdn.com");
  });

  it("keeps place labels above thermal polygons", () => {
    expect(source).toContain('layer.type === "symbol"');
    expect(source).toContain("}, firstLabelLayerId)");
  });

  it("offers opt-in device location and distinguishes context from coverage", () => {
    expect(source).toContain("new maplibregl.GeolocateControl");
    expect(source).toContain("trackUserLocation: false");
    expect(source).toContain("Streets and place labels provide geographic context only");
    expect(source).toContain("only inside validated HVA-Signal analysis zones");
  });
});
