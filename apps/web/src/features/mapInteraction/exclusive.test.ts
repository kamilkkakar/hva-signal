import { describe, expect, it } from "vitest";
import {
  bindExclusiveMapLayer,
  catalogForHistoricalRankMap,
  rankedFillCount,
} from "./exclusive";
import { historicalCatalog, snapshotCatalog } from "./fixtures";
import { hoverFromState } from "./detail";
import { presentMapInteraction } from "./present";
import { initialInteractionState, reduceInteraction } from "./state";
import { tableFromCatalog } from "./table";
import {
  ORDER_SHOWN_TITLE,
  ORDER_WITHHELD_STATUS_LOCK,
  ORDER_WITHHELD_TITLE,
} from "./policy";

describe("MAP-B titles and insufficient fills", () => {
  it("titles the authorized A layer as nighttime historical thermal order", () => {
    const catalog = historicalCatalog(true);
    const view = presentMapInteraction({
      catalog,
      state: initialInteractionState(),
    });
    expect(catalog.layer_title).toBe(ORDER_SHOWN_TITLE);
    expect(view.layerTitle).toBe("Nighttime historical thermal order");
  });

  it("titles the withheld A layer and keeps the status lock string", () => {
    const catalog = historicalCatalog(false);
    const view = presentMapInteraction({
      catalog,
      state: initialInteractionState(),
    });
    expect(catalog.layer_title).toBe(ORDER_WITHHELD_TITLE);
    expect(view.layerTitle).toBe("Order withheld — night too flat");
    expect(ORDER_WITHHELD_STATUS_LOCK).toBe(
      "THERMAL SPATIAL DIFFERENTIATION IS INSUFFICIENT FOR A DEFENSIBLE ORDERING",
    );
  });

  it("counts 0 ranked fills when the night is too flat, even with leftover order fields", () => {
    const catalog = historicalCatalog(false);
    expect(rankedFillCount(catalog)).toBe(0);
    expect(catalog.zones.every((zone) => zone.has_semantic_fill === false)).toBe(true);
    const fill = catalog.zones.filter((zone) => zone.has_semantic_fill).length;
    expect(fill).toBe(0);
  });

  it("counts authorized order participants as fills", () => {
    expect(rankedFillCount(historicalCatalog(true))).toBe(5);
  });
});

describe("B layer is not on the A rank map", () => {
  it("drops a selected-time snapshot handed to the historical rank bind", () => {
    expect(catalogForHistoricalRankMap(snapshotCatalog())).toBeNull();
    expect(catalogForHistoricalRankMap(historicalCatalog(true))?.kind).toBe(
      "historical_ordering",
    );
  });

  it("ignores a snapshot catalog when the exclusive lane is A", () => {
    const bound = bindExclusiveMapLayer({
      lane: "A",
      historical: historicalCatalog(true),
      snapshot: snapshotCatalog(),
    });
    expect(bound?.kind).toBe("historical_ordering");
    expect(bound?.zones.every((zone) => zone.value_kind !== "mean_c")).toBe(true);
  });

  it("ignores a historical order catalog when the exclusive lane is B", () => {
    const bound = bindExclusiveMapLayer({
      lane: "B",
      historical: historicalCatalog(true),
      snapshot: snapshotCatalog(),
    });
    expect(bound?.kind).toBe("selected_time_snapshot");
    expect(bound?.layer_title).toBe("Selected-Time Thermal Snapshot");
  });

  it("refuses to treat a historical catalog as a B snapshot", () => {
    const bound = bindExclusiveMapLayer({
      lane: "B",
      historical: historicalCatalog(true),
      snapshot: historicalCatalog(true),
    });
    expect(bound).toBeNull();
  });
});

describe("hover, click, and a11y table", () => {
  it("hover is transient and click persists on an authorized A catalog", () => {
    const catalog = historicalCatalog(true);
    const geoid = catalog.zones[0]?.geoid ?? "";
    let state = initialInteractionState();
    state = reduceInteraction(state, { type: "hover", geoid }, catalog);
    expect(hoverFromState(state, catalog)?.line).toBe(
      `Zone ${geoid} · Nighttime order 1 of 5`,
    );
    expect(state.selectedId).toBeNull();
    state = reduceInteraction(state, { type: "select", geoid }, catalog);
    state = reduceInteraction(state, { type: "hover", geoid: null }, catalog);
    expect(state.selectedId).toBe(geoid);
    expect(state.hoverId).toBeNull();
  });

  it("turns hover off when the order is withheld", () => {
    const catalog = historicalCatalog(false);
    const geoid = catalog.zones[0]?.geoid ?? "";
    const state = reduceInteraction(
      initialInteractionState(),
      { type: "hover", geoid },
      catalog,
    );
    expect(state.hoverId).toBeNull();
    expect(hoverFromState(state, catalog)).toBeNull();
    const view = presentMapInteraction({ catalog, state });
    expect(view.hover).toBeNull();
  });

  it("keeps the accessible zone table as the keyboard path", () => {
    const rows = tableFromCatalog(historicalCatalog(true));
    expect(rows.length).toBeGreaterThan(0);
    expect(rows.map((row) => row.geoid)).toEqual(
      [...rows.map((row) => row.geoid)].sort((a, b) => a.localeCompare(b)),
    );
    expect(rows[0]).toEqual(
      expect.objectContaining({
        geoid: expect.any(String),
        label: expect.any(String),
        value_display: expect.any(String),
        coverage: expect.any(String),
        time_label: expect.any(String),
        source_label: expect.any(String),
      }),
    );
    const withheld = tableFromCatalog(historicalCatalog(false));
    expect(withheld.every((row) => row.value_display === "—")).toBe(true);
  });
});
