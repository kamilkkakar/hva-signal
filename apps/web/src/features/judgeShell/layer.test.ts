import { describe, expect, it } from "vitest";
import {
  CONTEXTUAL_MAP_LAYER,
  DEFAULT_MAP_LAYER,
  mapLayerFromLimitations,
  THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT,
} from "@/utils/mapLayer";
import {
  JUDGE_LAYER_ORDER,
  JUDGE_LAYER_WINDOW,
  JUDGE_LAYER_WITHHELD,
  judgeMapLayer,
} from "./layer";

describe("judge map layer titles", () => {
  it("uses the window title before a result", () => {
    const layer = judgeMapLayer(
      mapLayerFromLimitations([]),
      { state: "INSUFFICIENT_EVIDENCE", scores: [] },
      false,
    );
    expect(layer.label).toBe(JUDGE_LAYER_WINDOW);
    expect(layer.label).not.toBe(DEFAULT_MAP_LAYER);
  });

  it("kills intervention and preparedness titles", () => {
    const withheld = judgeMapLayer(
      mapLayerFromLimitations([THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT]),
      { state: "INSUFFICIENT_EVIDENCE", scores: [] },
      true,
    );
    expect(withheld.label).toBe(JUDGE_LAYER_WITHHELD);
    expect(withheld.label).not.toBe(CONTEXTUAL_MAP_LAYER);
    expect(withheld.label.toLowerCase()).not.toContain("intervention");
    expect(withheld.label.toLowerCase()).not.toContain("preparedness");

    const shown = judgeMapLayer(
      mapLayerFromLimitations([]),
      { state: "READY", scores: [] },
      true,
    );
    expect(shown.label).toBe(JUDGE_LAYER_ORDER);
    expect(shown.label).not.toBe(DEFAULT_MAP_LAYER);
  });
});
