import { describe, expect, it } from "vitest";
import { buildOutlookPlan, type OutlookEngineInput } from "./outlookEngine";

const BASE: OutlookEngineInput = {
  cityLabel: "Phoenix",
  observationMode: "published",
  liveState: "idle",
  spatialState: "withheld",
  hasHistoricalMatchedEvidence: true,
  observedInstantCount: 3,
};

describe("outlookEngine", () => {
  it("responds to withheld spatial evidence with temporal evidence, not ranking", () => {
    const plan = buildOutlookPlan(BASE);

    expect(plan.state).toBe("evidence_limited");
    expect(plan.steps[0]?.id).toBe("add-temporal-evidence");
    expect(plan.steps.map((step) => step.id)).toContain("review-matched-history");
    expect(plan.steps.every((step) => step.whyShown.length > 0)).toBe(true);
    expect(JSON.stringify(plan).toLowerCase()).not.toContain("priority score");
  });

  it("starts Live mode with the missing observation", () => {
    const plan = buildOutlookPlan({
      ...BASE,
      cityLabel: "Tucson",
      observationMode: "live",
      liveState: "idle",
      spatialState: "not_evaluated",
      hasHistoricalMatchedEvidence: false,
      observedInstantCount: 0,
    });

    expect(plan.state).toBe("needs_observation");
    expect(plan.steps[0]?.id).toBe("run-selected-time-observation");
    expect(plan.steps[0]?.whyShown).toContain("Tucson");
  });

  it("compares a completed Live result with the published observation", () => {
    const plan = buildOutlookPlan({
      ...BASE,
      observationMode: "live",
      liveState: "ready",
      spatialState: "not_evaluated",
    });

    expect(plan.steps.map((step) => step.id)).toContain("compare-published-observation");
    expect(plan.steps).toHaveLength(3);
  });

  it("asks whether a supported pattern persists", () => {
    const plan = buildOutlookPlan({ ...BASE, spatialState: "supported" });

    expect(plan.state).toBe("ready");
    expect(plan.steps[0]?.id).toBe("test-pattern-persistence");
    expect(plan.summary).toContain("persists");
  });
});
