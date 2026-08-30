import { describe, expect, it } from "vitest";
import { bindHistoricalPositions } from "./bind";
import {
  AXIS_HIGH,
  AXIS_LOW,
  STAMP_ORDERING_SUPPORTED,
  STAMP_ORDERING_WITHHELD,
} from "./copy";
import { clusteredResult, SELECTED_CLUSTERED_ID, separatedResult } from "./fixtures";
import { chartChromeLeaksMethod, presentHistoricalPosition } from "./presentation";

describe("presentHistoricalPosition", () => {
  it("shows clustered marks as ORDERING WITHHELD without method nouns", () => {
    const view = presentHistoricalPosition(
      bindHistoricalPositions({
        result: clusteredResult(),
        selectedZoneId: SELECTED_CLUSTERED_ID,
      }),
    );
    expect(view.visible).toBe(true);
    expect(view.marks).toHaveLength(25);
    expect(view.comparisonStamp).toBe(STAMP_ORDERING_WITHHELD);
    expect(view.axisLow).toBe(AXIS_LOW);
    expect(view.axisHigh).toBe(AXIS_HIGH);
    expect(view.selectedExact).toBe("0.200");
    expect(view.frameCaption).toBe("03:00 · 2022–2024 same hour");
    expect(chartChromeLeaksMethod(view)).toBe(false);
  });

  it("shows separated marks as ORDERING SUPPORTED", () => {
    const view = presentHistoricalPosition(
      bindHistoricalPositions({ result: separatedResult() }),
    );
    expect(view.comparisonStamp).toBe(STAMP_ORDERING_SUPPORTED);
    expect(view.selected).toBeNull();
    expect(view.selectedExact).toBeNull();
    expect(chartChromeLeaksMethod(view)).toBe(false);
  });

  it("hides the figure when history did not produce positions", () => {
    const view = presentHistoricalPosition(
      bindHistoricalPositions({
        result: { thermal_differentiation_state: "SUFFICIENT", zones: [] },
      }),
    );
    expect(view.visible).toBe(false);
    expect(view.marks).toHaveLength(0);
    expect(view.comparisonStamp).toBeNull();
    expect(view.frameCaption).toBeNull();
  });
});
