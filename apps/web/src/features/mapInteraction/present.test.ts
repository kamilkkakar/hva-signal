import { describe, expect, it } from "vitest";
import { detailFromState, hoverFromState } from "./detail";
import { emptyInteractionCatalog, historicalCatalog, snapshotCatalog } from "./fixtures";
import { historicalPositionLegend } from "@/features/mapEncoding";
import { highlightFillPaint, highlightHatchPaint, highlightLinePaint } from "./highlight";
import { legendFromCatalog } from "./legend";
import { DECORATIVE_MAP_FORBIDDEN } from "./policy";
import { presentMapInteraction } from "./present";
import { initialInteractionState, reduceInteraction } from "./state";
import { tableFromCatalog } from "./table";

describe("presentMapInteraction", () => {
  it("stays gated off when the stitch override is false", () => {
    const view = presentMapInteraction({
      enabled: false,
      catalog: snapshotCatalog(),
      state: initialInteractionState(),
    });
    expect(view.visualState).toBe("gated_off");
    expect(view.canvasAllowed).toBe(false);
    expect(view.detail).toBeNull();
    expect(view.tableRows).toHaveLength(0);
    expect(view.decorative).toBe(false);
  });

  it("defaults on for the I-MAP stitch branch", () => {
    const view = presentMapInteraction({
      catalog: snapshotCatalog(),
      state: initialInteractionState(),
    });
    expect(view.gated).toBe(false);
    expect(view.visualState).not.toBe("gated_off");
    expect(view.canvasAllowed).toBe(true);
  });

  it("lets map state drive hover, selection, and detail", () => {
    const catalog = snapshotCatalog();
    const geoid = catalog.zones[0]?.geoid ?? "";
    let state = initialInteractionState();
    state = reduceInteraction(state, { type: "hover", geoid }, catalog);
    let view = presentMapInteraction({ enabled: true, catalog, state });
    expect(view.hover?.geoid).toBe(geoid);
    expect(view.hover?.value_display).toBe(catalog.zones[0]?.value_display);
    expect(view.hover?.line).toContain(geoid);
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
    expect(view.positionLegendMode).toBe("insufficient");
    expect(view.legend).toHaveLength(1);
    expect(view.legend[0]?.id).toBe("outline");
    const pos = historicalPositionLegend(view.positionLegendMode);
    expect(pos.stops).toEqual([]);
    expect(pos.hatchSamples).toEqual([]);
    expect(pos.axis).toBeNull();
  });

  it("binds an authorized historical catalog to a multi-stop position legend, not one sage swatch", () => {
    const catalog = historicalCatalog(true);
    const view = presentMapInteraction({
      enabled: true,
      catalog,
      state: initialInteractionState(),
    });
    expect(view.positionLegendMode).toBe("sufficient");
    expect(view.legend).toEqual([]);
    expect(JSON.stringify(view.legend)).not.toContain("#9aa392");
    expect(JSON.stringify(view)).not.toMatch(/color encoding is the legend/i);
    const pos = historicalPositionLegend(view.positionLegendMode);
    expect(pos.stops.length).toBeGreaterThan(1);
    expect(pos.axis).toBe("LOWER HISTORICAL POSITION ↔ HIGHER HISTORICAL POSITION");
    expect(pos.hatchSamples.length).toBe(3);
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

  it("paints no ranking fill when the night is unauthorized", () => {
    const catalog = historicalCatalog(false);
    const state = initialInteractionState();
    const fill = highlightFillPaint(catalog, state);
    expect(fill["fill-opacity"]).toBe(0);
    expect(JSON.stringify(fill)).not.toMatch(/interpolate/i);
  });

  it("uses historical-position encoding when an order is authorized", () => {
    const catalog = historicalCatalog(true);
    const state = initialInteractionState();
    const fill = highlightFillPaint(catalog, state);
    const hatch = highlightHatchPaint(catalog, state);
    expect(JSON.stringify(fill)).toMatch(/interpolate/i);
    expect(JSON.stringify(fill)).not.toMatch(/°C/);
    expect(hatch["fill-opacity"]).toBeGreaterThan(0);
    expect(JSON.stringify(hatch)).toContain("hva-pos-hatch");
    expect(highlightHatchPaint(historicalCatalog(false), state)["fill-opacity"]).toBe(0);
  });
});
