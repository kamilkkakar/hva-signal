import { describe, expect, it } from "vitest";
import type { AnalysisResultStub } from "@/api/analysisJobs";
import { signalAInputFromResult } from "./fromResult";
import { judgeChromeStrings, presentSignalA } from "./presentation";

function sufficient(): AnalysisResultStub {
  return {
    thermal_differentiation_state: "SUFFICIENT",
    hazard_spread: { differentiation_state: "SUFFICIENT" },
    zones: [
      { zone_id: "1", thermal_ordering_permitted: true, q_A: 0.34 },
      { zone_id: "2", thermal_ordering_permitted: true, q_A: 0.12 },
    ],
  };
}

function insufficient(): AnalysisResultStub {
  return {
    thermal_differentiation_state: "INSUFFICIENT",
    hazard_spread: {
      differentiation_state: "INSUFFICIENT",
      observed_spread: 0.04,
      floor: 0.1,
    },
    zones: [{ zone_id: "1", thermal_ordering_permitted: false, q_A: 0.2 }],
  };
}

describe("signalAInputFromResult", () => {
  it("reads existing SUFFICIENT / INSUFFICIENT bits and ignores q_A values", () => {
    const shown = presentSignalA(
      signalAInputFromResult({
        status: "complete",
        result: sufficient(),
        zoneId: "1",
        order: 2,
      }),
    );
    expect(shown.kind).toBe("order_shown");
    expect(shown.stamp).toBe("SPATIAL ORDERING SUPPORTED");
    expect(shown.hoverLine).toContain("order 2 of 25");
    expect(shown.method.q_A).toContain("q_A");
    const shownChrome = judgeChromeStrings(shown).join("\n");
    expect(shownChrome).not.toContain("0.34");
    expect(shownChrome).not.toContain("q_A");

    const withheld = presentSignalA(
      signalAInputFromResult({ status: "complete", result: insufficient() }),
    );
    expect(withheld.kind).toBe("order_withheld");
    expect(withheld.insufficientIsFeature).toBe(true);
    expect(withheld.rankedFillCount).toBe(0);
    const withheldChrome = judgeChromeStrings(withheld).join("\n");
    expect(withheldChrome).not.toContain("0.04");
    expect(withheldChrome).not.toContain("0.10");
  });

  it("maps missing reference to HISTORY NOT PREPARED, not withhold", () => {
    const view = presentSignalA(
      signalAInputFromResult({
        status: "complete",
        result: { zones: [] },
        historyPrepared: false,
      }),
    );
    expect(view.stamp).toBe("HISTORY NOT PREPARED");
    expect(view.kind).not.toBe("order_withheld");
  });
});
