import { describe, expect, it } from "vitest";
import {
  HISTORY_UNAVAILABLE,
  RANKING_WITHHELD_BODY,
  historicalPositionSentence,
} from "./copy";
import {
  presentHistoricalHero,
  presentHistoricalPosition,
  presentSpatialDifferentiation,
} from "./historicalPosition";

describe("historical position vs spatial differentiation", () => {
  it("publishes own-area historical percent when order is shown", () => {
    const view = presentHistoricalPosition(
      {
        thermal_differentiation_state: "SUFFICIENT",
        zones: [
          { zone_id: "04013107401", thermal_ordering_permitted: true, q_A: 0.812 },
        ],
      },
      "04013107401",
    );
    expect(view.status).toBe("available");
    expect(view.sentence).toBe(historicalPositionSentence(0.812));
    expect(view.percent).toBe(81);
    expect(view.sentence).not.toContain("q_A");
    expect(view.sentence).not.toMatch(/ranking withheld/i);
  });

  it("keeps historical unavailable separate from spatial ranking withheld", () => {
    const result = {
      thermal_differentiation_state: "INSUFFICIENT" as const,
      zones: [
        { zone_id: "04013107401", thermal_ordering_permitted: false, q_A: 0.812 },
      ],
    };
    const history = presentHistoricalPosition(result, "04013107401");
    const spatial = presentSpatialDifferentiation(result, "04013107401");
    expect(history.status).toBe("unavailable");
    expect(history.sentence).toBe(HISTORY_UNAVAILABLE);
    expect(history.sentence).not.toMatch(/too small to support/i);
    expect(spatial.status).toBe("withheld");
    expect(spatial.sentence).toBe(RANKING_WITHHELD_BODY);
  });

  it("marks spatial comparison supported when differentiation is sufficient", () => {
    const spatial = presentSpatialDifferentiation(
      {
        thermal_differentiation_state: "SUFFICIENT",
        zones: [
          { zone_id: "04013107401", thermal_ordering_permitted: true, q_A: 0.5 },
        ],
      },
      "04013107401",
    );
    expect(spatial.status).toBe("supported");
  });

  it("legacy hero helper still exposes withheld for consumers", () => {
    const view = presentHistoricalHero(
      {
        thermal_differentiation_state: "INSUFFICIENT",
        zones: [
          { zone_id: "04013107401", thermal_ordering_permitted: false, q_A: 0.812 },
        ],
      },
      "04013107401",
    );
    expect(view.withheld).toBe(true);
    expect(view.sentence).toBe(RANKING_WITHHELD_BODY);
  });
});
