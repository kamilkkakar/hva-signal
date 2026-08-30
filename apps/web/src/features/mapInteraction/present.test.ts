import { describe, expect, it } from "vitest";
import { detailFromState, hoverFromState } from "./detail";
import { emptyInteractionCatalog, historicalCatalog, snapshotCatalog } from "./fixtures";
import { highlightFillPaint, highlightLinePaint } from "./highlight";
import { legendFromCatalog } from "./legend";
import { DECORATIVE_MAP_FORBIDDEN } from "./policy";
import { presentMapInteraction } from "./present";
import { initialInteractionState, reduceInteraction } from "./state";
import { tableFromCatalog } from "./table";

describe("presentMapInteraction", () => {
  it("stays gated off by default", () => {
    const view = presentMapInteraction({
      catalog: snapshotCatalog(),
      state: initialInteractionState(),
    });
    expect(view.visualState).toBe("gated_off");
    expect(view.canvasAllowed).toBe(false);
    expect(view.detail).toBeNull();
    expect(view.tableRows).toHaveLength(0);
    expect(view.decorative).toBe(false);
  });

  it("lets map state drive hover, selection, and detail", () => {
    const catalog = snapshotCatalog();
    const geoid = catalog.zones[0]?.geoid ?? "";
    let state = initialInteractionState();
    state = reduceInteraction(state, { type: "hover", geoid }, catalog);
    let view = presentMapInteraction({ enabled: true, catalog, state });
    expect(view.hover?.geoid).toBe(geoid);
    expect(view.hover?.value_display).toBe(catalog.zones[0]?.value_display);
    expect(view.detail).toBeNull();

    state = reduceInteraction(state, { type: "select", geoid }, catalog);
    state = reduceInteraction(state, { type: "hover", geoid: null }, catalog);
    view = presentMapInteraction({ enabled: true, catalog, state });
    expect(view.hover).toBeNull();
    expect(view.detail?.geoid).toBe(geoid);
    expect(view.detail?.label).toBe(catalog.zones[0]?.label);
    expect(view.detail?.value_display).toBe(catalog.zones[0]?.value_display);
    expect(view.detail?.coverage).toBe("valid");
    expect(view.detail?.time_label).toContain("America/Phoenix");
    expect(view.detail?.source_label).toBe("REPLAY");
  });

  it("clears detail when the layer is cleared and restores an honest legend", () => {
    const catalog = snapshotCatalog();
    const geoid = catalog.zones[0]?.geoid ?? "";
    let state = reduceInteraction(initialInteractionState(), { type: "select", geoid }, catalog);
    state = reduceInteraction(state, { type: "clear_layer" }, catalog);
    const view = presentMapInteraction({ enabled: true, catalog, state });
    expect(view.visualState).toBe("layer_cleared");
    expect(view.detail).toBeNull();
    expect(view.hover).toBeNull();
    expect(view.legend.some((item) => item.id === "cleared")).toBe(true);
    expect(view.canRestoreLayer).toBe(true);
    expect(detailFromState(state, catalog)).toBeNull();
    expect(hoverFromState(state, catalog)).toBeNull();
  });

  it("binds the snapshot legend to shared-fill semantics, not a temperature ramp", () => {
    const legend = legendFromCatalog(snapshotCatalog(), true);
    expect(legend.map((item) => item.id)).toEqual(["valid", "missing"]);
    expect(legend[0]?.meaning).toMatch(/not stretched/i);
  });

  it("binds an unauthorized historical catalog to outline-only legend", () => {
    const catalog = historicalCatalog(false);
    const view = presentMapInteraction({
      enabled: true,
      catalog,
      state: initialInteractionState(),
    });
    expect(view.visualState).toBe("outline_only");
    expect(view.legend).toHaveLength(1);
    expect(view.legend[0]?.id).toBe("outline");
  });

  it("sorts the accessible table by GEOID and keeps the six judge fields", () => {
    const rows = tableFromCatalog(snapshotCatalog());
    const ids = rows.map((row) => row.geoid);
    expect(ids).toEqual([...ids].sort((a, b) => a.localeCompare(b)));
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
  });

  it("withholds the canvas when there is nothing to inspect", () => {
    const view = presentMapInteraction({
      enabled: true,
      catalog: emptyInteractionCatalog(),
      state: initialInteractionState(),
    });
    expect(view.visualState).toBe("empty");
    expect(view.canvasAllowed).toBe(false);
    expect(DECORATIVE_MAP_FORBIDDEN).toBe(true);
    expect(view.decorative).toBe(false);
  });

  it("does not interpolate values into fill paint", () => {
    const catalog = snapshotCatalog();
    const state = initialInteractionState();
    const fill = highlightFillPaint(catalog, state);
    const line = highlightLinePaint(state);
    expect(JSON.stringify(fill)).not.toMatch(/interpolate/i);
    expect(JSON.stringify(line)).not.toMatch(/interpolate/i);
    expect(fill["fill-color"]).toBe("#9aa392");
  });
});
