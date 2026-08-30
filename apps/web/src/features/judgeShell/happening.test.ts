import { describe, expect, it } from "vitest";
import {
  INSUFFICIENT_REFERENCE,
  THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT,
} from "@/utils/mapLayer";
import { happeningView } from "./happening";

describe("happening stamps", () => {
  it("stays NOT REQUESTED before a job", () => {
    const view = happeningView({
      status: null,
      busy: false,
      stalled: false,
      rankingState: "INSUFFICIENT_EVIDENCE",
      limitations: [],
    });
    expect(view.stamp).toBe("NOT REQUESTED");
    expect(view.line.toLowerCase()).not.toContain("insufficient_evidence");
  });

  it("stamps ORDER SHOWN when ranking is ready", () => {
    const view = happeningView({
      status: "complete",
      busy: false,
      stalled: false,
      rankingState: "READY",
      limitations: [],
    });
    expect(view.stamp).toBe("ORDER SHOWN");
  });

  it("stamps ORDER WITHHELD on a flat night", () => {
    const view = happeningView({
      status: "complete",
      busy: false,
      stalled: false,
      rankingState: "INSUFFICIENT_EVIDENCE",
      limitations: [THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT],
    });
    expect(view.stamp).toBe("ORDER WITHHELD");
  });

  it("stamps HISTORY NOT PREPARED when reference is missing", () => {
    const view = happeningView({
      status: "complete",
      busy: false,
      stalled: false,
      rankingState: "INSUFFICIENT_EVIDENCE",
      limitations: [INSUFFICIENT_REFERENCE],
    });
    expect(view.stamp).toBe("HISTORY NOT PREPARED");
  });

  it("stamps WORKING while a replay is in flight", () => {
    const view = happeningView({
      status: "computing",
      busy: true,
      stalled: false,
      rankingState: "INSUFFICIENT_EVIDENCE",
      limitations: [],
    });
    expect(view.stamp).toBe("WORKING");
  });

  it("stamps JOB LOST for unknown_job", () => {
    const view = happeningView({
      status: "unknown_job",
      busy: false,
      stalled: false,
      rankingState: "INSUFFICIENT_EVIDENCE",
      limitations: [],
    });
    expect(view.stamp).toBe("JOB LOST");
  });
});
