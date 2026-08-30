import { describe, expect, it } from "vitest";
import { canvasAllowed } from "./catalog";
import { emptyInteractionCatalog, historicalCatalog, snapshotCatalog } from "./fixtures";
import { catalogFromHistorical } from "./fromHistorical";
import { catalogFromSnapshot } from "./fromSnapshot";
import { productSourceLabel } from "./policy";

describe("productSourceLabel", () => {
  it("maps vendor enums to product labels without naming the vendor", () => {
    expect(productSourceLabel("replay")).toBe("REPLAY");
    expect(productSourceLabel("cached")).toBe("CACHED");
    expect(productSourceLabel("fortyguard_cached")).toBe("CACHED");
    expect(productSourceLabel("fortyguard_live")).toBe("LIVE");
    expect(productSourceLabel("partial")).toBe("PARTIAL");
    expect(productSourceLabel(null)).toBe("UNAVAILABLE");
  });
});

describe("catalogFromSnapshot", () => {
  it("binds GEOID, absolute °C, coverage, time, and source", () => {
    const catalog = snapshotCatalog(true);
    expect(catalog.kind).toBe("selected_time_snapshot");
    expect(catalog.zones).toHaveLength(5);
    expect(catalog.zones[0]?.value_kind).toBe("mean_c");
    expect(catalog.zones[0]?.source_label).toBe("REPLAY");
    expect(catalog.zones[0]?.time_label).toContain("2024-07-15T15:00:00");
    expect(catalog.zones[0]?.time_label).toContain("America/Phoenix");
    const missing = catalog.zones.find((zone) => zone.geoid === "FIX-0455000-05");
    expect(missing?.value_display).toBe("—");
    expect(missing?.coverage).toBe("missing");
    expect(missing?.has_semantic_fill).toBe(false);
  });

  it("does not coerce a missing mean to 0 °C", () => {
    const catalog = catalogFromSnapshot({
      zones: [{ zone_id: "Z-1", mean_temperature_c: null, coverage_status: "missing" }],
      source: "replay",
    });
    expect(catalog.zones[0]?.value_display).toBe("—");
  });
});

describe("catalogFromHistorical", () => {
  it("exposes nighttime order text when ordering is authorized, never q_A", () => {
    const catalog = historicalCatalog(true);
    expect(catalog.kind).toBe("historical_ordering");
    expect(catalog.layer_title).toBe("Nighttime historical thermal order");
    expect(catalog.fill_authorized).toBe(true);
    expect(catalog.zones[0]?.value_kind).toBe("order");
    expect(catalog.zones[0]?.value_display).toBe("Nighttime order 1 of 5");
    expect(catalog.zones[0]?.label).toBe("Locator 1");
    expect(catalog.zones[0]?.source_label).toBe("REPLAY");
    expect(catalog.zones.every((zone) => !zone.value_display.includes("0.2"))).toBe(true);
  });

  it("stays outline-only when ranking is not authorized", () => {
    const catalog = historicalCatalog(false);
    expect(catalog.kind).toBe("aoi_outline");
    expect(catalog.layer_title).toBe("Order withheld — night too flat");
    expect(catalog.fill_authorized).toBe(false);
    expect(catalog.zones.every((zone) => zone.has_semantic_fill === false)).toBe(true);
    expect(catalog.zones.every((zone) => zone.value_display === "—")).toBe(true);
    expect(catalog.zones[0]?.coverage).toBe("order withheld");
  });

  it("does not invent fill authorization from leftover q_A or backend_order", () => {
    const catalog = catalogFromHistorical({
      features: [
        {
          properties: {
            GEOID: "040139999",
            q_A: 0.9,
            backend_order: 1,
            thermal_ordering_permitted: true,
          },
        },
      ],
      fillAuthorized: false,
      dataMode: "replay",
    });
    expect(catalog.fill_authorized).toBe(false);
    expect(catalog.zones[0]?.has_semantic_fill).toBe(false);
    expect(catalog.zones[0]?.value_display).toBe("—");
    expect(catalog.zones[0]?.value_kind).toBe("none");
  });
});

describe("canvasAllowed", () => {
  it("refuses a decorative empty canvas", () => {
    expect(canvasAllowed(null, true)).toBe(false);
    expect(canvasAllowed(emptyInteractionCatalog(), true)).toBe(false);
    expect(canvasAllowed(snapshotCatalog(), true)).toBe(true);
  });
});
