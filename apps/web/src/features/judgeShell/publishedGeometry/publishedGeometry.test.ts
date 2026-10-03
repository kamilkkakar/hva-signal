import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { publishedPhoenixGeometry } from "./index";
import { buildJudgeMapCatalog } from "../mapCatalog";

const source = new URL("../../../../../../data/areas/phoenix-demo/", import.meta.url);

describe("published Phoenix geometry", () => {
  it("ships the exact server-owned frozen bytes and identity", () => {
    const original = readFileSync(new URL("geometry.geojson", source));
    const shipped = readFileSync(new URL("./phoenix-demo.json", import.meta.url));
    const manifest = JSON.parse(readFileSync(new URL("manifest.json", source), "utf8"));
    expect(shipped.equals(original)).toBe(true);
    expect(createHash("sha256").update(shipped).digest("hex")).toBe(manifest.geometry_sha256);
    expect(publishedPhoenixGeometry("phoenix-demo")?.geometrySha256).toBe(manifest.geometry_sha256);
  });
  it("binds every published temperature without a network request", () => {
    const catalog = buildJudgeMapCatalog({
      geometry: publishedPhoenixGeometry("phoenix-demo"),
      areaId: "phoenix-demo", result: null, jobStatus: null,
    });
    expect(catalog?.collection.features).toHaveLength(25);
    expect(catalog?.zones.filter(zone => zone.has_semantic_fill)).toHaveLength(25);
    expect(catalog?.fill_authorized).toBe(true);
  });
  it("never substitutes Phoenix geometry for another AOI", () => {
    expect(publishedPhoenixGeometry("tucson")).toBeNull();
  });
});
