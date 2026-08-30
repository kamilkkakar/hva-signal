import { describe, expect, it } from "vitest";
import { snapshotCatalog } from "./fixtures";
import { reduceInteraction, initialInteractionState } from "./state";

const catalog = snapshotCatalog();
const first = catalog.zones[0]?.geoid ?? "";
const second = catalog.zones[1]?.geoid ?? "";

describe("reduceInteraction", () => {
  it("hover is transient and does not write selection", () => {
    let state = initialInteractionState();
    state = reduceInteraction(state, { type: "hover", geoid: first }, catalog);
    expect(state.hoverId).toBe(first);
    expect(state.selectedId).toBeNull();
    state = reduceInteraction(state, { type: "hover", geoid: null }, catalog);
    expect(state.hoverId).toBeNull();
    expect(state.selectedId).toBeNull();
  });

  it("click persists after hover leave and toggles the same GEOID", () => {
    let state = initialInteractionState();
    state = reduceInteraction(state, { type: "select", geoid: first }, catalog);
    state = reduceInteraction(state, { type: "hover", geoid: second }, catalog);
    state = reduceInteraction(state, { type: "hover", geoid: null }, catalog);
    expect(state.selectedId).toBe(first);
    expect(state.hoverId).toBeNull();
    state = reduceInteraction(state, { type: "select", geoid: first }, catalog);
    expect(state.selectedId).toBeNull();
  });

  it("clear layer drops hover, selection, and fill; restore does not invent a selection", () => {
    let state = initialInteractionState();
    state = reduceInteraction(state, { type: "select", geoid: first }, catalog);
    state = reduceInteraction(state, { type: "hover", geoid: second }, catalog);
    state = reduceInteraction(state, { type: "clear_layer" }, catalog);
    expect(state.layerActive).toBe(false);
    expect(state.hoverId).toBeNull();
    expect(state.selectedId).toBeNull();
    state = reduceInteraction(state, { type: "restore_layer" }, catalog);
    expect(state.layerActive).toBe(true);
    expect(state.selectedId).toBeNull();
  });

  it("hover is ignored while the layer is cleared", () => {
    let state = initialInteractionState();
    state = reduceInteraction(state, { type: "clear_layer" }, catalog);
    state = reduceInteraction(state, { type: "hover", geoid: first }, catalog);
    expect(state.hoverId).toBeNull();
  });

  it("fit and reset increment the camera token; reset clears hover only", () => {
    let state = initialInteractionState();
    state = reduceInteraction(state, { type: "select", geoid: first }, catalog);
    state = reduceInteraction(state, { type: "hover", geoid: second }, catalog);
    state = reduceInteraction(state, { type: "fit_aoi" }, catalog);
    expect(state.fitGeneration).toBe(1);
    expect(state.selectedId).toBe(first);
    state = reduceInteraction(state, { type: "reset_aoi" }, catalog);
    expect(state.fitGeneration).toBe(2);
    expect(state.hoverId).toBeNull();
    expect(state.selectedId).toBe(first);
  });

  it("ignores unknown GEOIDs", () => {
    const state = reduceInteraction(
      initialInteractionState(),
      { type: "select", geoid: "not-a-zone" },
      catalog,
    );
    expect(state.selectedId).toBeNull();
  });
});
