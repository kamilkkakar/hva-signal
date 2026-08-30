import { describe, expect, it } from "vitest";
import type { AnalysisResultStub } from "@/api/analysisJobs";
import {
  INSUFFICIENT_STAMP,
  NOT_EVALUATED_STAMP,
  SUFFICIENT_STAMP,
} from "./copy";
import { presentActionFraming } from "./framing";

function zone(id: string, permitted: boolean): NonNullable<AnalysisResultStub["zones"]>[number] {
  return {
    zone_id: id,
    ranked: permitted,
    thermal_ordering_permitted: permitted,
  };
}

function sufficientResult(): AnalysisResultStub {
  return {
    thermal_differentiation_state: "SUFFICIENT",
    hazard_spread: {
      differentiation_state: "SUFFICIENT",
      observed_spread: 0.13548387096774192,
    },
    zones: Array.from({ length: 25 }, (_, index) =>
      zone(String(index + 1).padStart(11, "0"), true),
    ),
  };
}

function insufficientResult(): AnalysisResultStub {
  return {
    thermal_differentiation_state: "INSUFFICIENT",
    system_limitations: ["THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT"],
    hazard_spread: {
      differentiation_state: "INSUFFICIENT",
      observed_spread: 0.0439665471923536,
    },
    zones: Array.from({ length: 25 }, (_, index) =>
      zone(String(index + 1).padStart(11, "0"), false),
    ),
  };
}

describe("presentActionFraming", () => {
  it("authorizes sufficient only when Decision 8 and zone permission agree", () => {
    const view = presentActionFraming({
      status: "complete",
      result: sufficientResult(),
    });
    expect(view.kind).toBe("sufficient");
    expect(view.stamp).toBe(SUFFICIENT_STAMP);
    expect(view.supports).toContain("one input");
  });

  it("withholds ranking on Decision 8 insufficient", () => {
    const view = presentActionFraming({
      status: "complete",
      result: insufficientResult(),
    });
    expect(view.kind).toBe("insufficient");
    expect(view.stamp).toBe(INSUFFICIENT_STAMP);
    expect(view.supports).toBe(
      "Do not use thermal ranking alone for zone prioritization.",
    );
  });

  it("does not treat insufficient reference as Decision 8 insufficient", () => {
    const view = presentActionFraming({
      status: "complete",
      result: {
        system_limitations: ["INSUFFICIENT_REFERENCE"],
        thermal_differentiation_state: "NOT_EVALUATED",
        hazard_spread: { differentiation_state: "NOT_EVALUATED" },
      },
    });
    expect(view.kind).toBe("not_evaluated");
    expect(view.stamp).toBe(NOT_EVALUATED_STAMP);
    expect(view.supports).toContain("not treated as safe");
  });

  it("fails closed when SUFFICIENT is claimed without permitted zones", () => {
    const view = presentActionFraming({
      status: "complete",
      result: {
        thermal_differentiation_state: "SUFFICIENT",
        hazard_spread: { differentiation_state: "SUFFICIENT" },
        zones: [zone("04013980000", false)],
      },
    });
    expect(view.kind).toBe("not_evaluated");
  });

  it("awaits in-flight jobs and does not invent an order", () => {
    const view = presentActionFraming({
      status: "validating_hazard_spread",
      result: null,
    });
    expect(view.kind).toBe("awaiting");
    expect(view.supports).toContain("No spatial order is authorized yet");
  });
});
