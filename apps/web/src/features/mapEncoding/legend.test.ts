import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { historicalPositionLegend, legendModeFromMap } from "./legend";
import { FORBIDDEN_LEGEND_PHRASES, SIGNAL_A_POS_STOPS } from "./tokens";

describe("historical position legend", () => {
  it("names the sufficient axis and keeps the sequential stops", () => {
    const view = historicalPositionLegend("sufficient");
    expect(view.axis).toBe("LOWER HISTORICAL POSITION ↔ HIGHER HISTORICAL POSITION");
    expect(view.lowLabel).toBe("LOWER HISTORICAL POSITION");
    expect(view.highLabel).toBe("HIGHER HISTORICAL POSITION");
    expect(view.stops).toEqual([...SIGNAL_A_POS_STOPS]);
    expect(view.hatchSamples).toHaveLength(3);
    expect(view.outlineSwatch).toBeNull();
  });

  it("does not retain ranking colors when position is withheld", () => {
    const view = historicalPositionLegend("insufficient");
    expect(view.axis).toBeNull();
    expect(view.stops).toEqual([]);
    expect(view.hatchSamples).toEqual([]);
    expect(view.outlineSwatch).toBe("#4e5748");
    expect(view.denial).toMatch(/not shown/i);
    expect(view.denial).toMatch(/no ranking colors/i);
  });

  it("maps map visual state without showing a ramp on idle or error", () => {
    expect(
      legendModeFromMap({ visualState: "sufficient", thermalOrderingVisible: true }),
    ).toBe("sufficient");
    expect(
      legendModeFromMap({
        visualState: "insufficient",
        thermalOrderingVisible: false,
      }),
    ).toBe("insufficient");
    expect(
      legendModeFromMap({ visualState: "idle", thermalOrderingVisible: false }),
    ).toBe("idle");
    expect(historicalPositionLegend("idle").stops).toEqual([]);
    expect(historicalPositionLegend("error").stops).toEqual([]);
  });

  it("keeps published legend copy off the forbidden axis", () => {
    const modes = ["sufficient", "insufficient", "idle", "loading", "error"] as const;
    const blob = modes
      .flatMap((mode) => {
        const view = historicalPositionLegend(mode);
        return [view.axis, view.lowLabel, view.highLabel, view.denial, view.hatchNote];
      })
      .filter((part): part is string => Boolean(part))
      .join("\n")
      .toLowerCase();
    for (const phrase of FORBIDDEN_LEGEND_PHRASES) {
      expect(blob, phrase).not.toContain(phrase);
    }
    const source = readFileSync(
      join(dirname(fileURLToPath(import.meta.url)), "HistoricalPositionLegend.tsx"),
      "utf8",
    ).toLowerCase();
    expect(source).not.toContain("safe");
    expect(source).not.toContain("danger");
  });
});
