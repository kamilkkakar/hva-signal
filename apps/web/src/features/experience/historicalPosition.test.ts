import { describe, expect, it } from "vitest";
import { HISTORY_UNAVAILABLE, HISTORY_WITHHELD, historicalPositionSentence } from "./copy";
import { presentHistoricalHero } from "./historicalPosition";

describe("historical position hero bind", () => {
  it("publishes a percent sentence only when spatial ranking is supported", () => {
    const view = presentHistoricalHero(
      {
        thermal_differentiation_state: "SUFFICIENT",
        zones: [
          { zone_id: "04013107401", thermal_ordering_permitted: true, q_A: 0.812 },
        ],
      },
      "04013107401",
    );
    expect(view.sentence).toBe(historicalPositionSentence(0.812));
    expect(view.percent).toBe(81);
    expect(view.withheld).toBe(false);
    expect(view.sentence).not.toContain("q_A");
  });

  it("withholds position language when the spatial ranking is withheld", () => {
    const view = presentHistoricalHero(
      {
        thermal_differentiation_state: "INSUFFICIENT",
        zones: [
          { zone_id: "04013107401", thermal_ordering_permitted: false, q_A: 0.812 },
        ],
      },
      "04013107401",
    );
    expect(view.sentence).toBe(HISTORY_WITHHELD);
    expect(view.percent).toBeNull();
    expect(view.withheld).toBe(true);
    expect(view.sentence).not.toContain("q_A");
    expect(view.sentence).not.toContain("Decision 8");
  });

  it("explains absence when no pane exists", () => {
    const view = presentHistoricalHero(null, "04013107401");
    expect(view.sentence).toBe(HISTORY_UNAVAILABLE);
    expect(view.percent).toBeNull();
  });
});
