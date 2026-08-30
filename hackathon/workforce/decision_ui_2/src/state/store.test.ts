import { describe, expect, it } from "vitest";
import { resetDecisionStore, useDecisionStore } from "./store";

describe("decision store", () => {
  it("syncs map mode when the question changes and records area selection", () => {
    resetDecisionStore();
    useDecisionStore.getState().selectQuestion("heat-over-day");
    expect(useDecisionStore.getState().mapModeId).toBe("daily_profile");
    useDecisionStore.getState().selectArea("area-9");
    expect(useDecisionStore.getState().selectedAreaId).toBe("area-9");
    useDecisionStore.getState().selectArea("area-9");
    expect(useDecisionStore.getState().selectedAreaId).toBeNull();
  });
});
