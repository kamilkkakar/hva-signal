import { describe, expect, it } from "vitest";
import { sourceBannerLabel } from "./sourceBanner";

describe("sourceBannerLabel", () => {
  it("is UNAVAILABLE when no job or provenance exists", () => {
    expect(sourceBannerLabel({ status: null })).toBe("UNAVAILABLE");
  });

  it("maps thermal sources without claiming live on replay", () => {
    expect(
      sourceBannerLabel({ status: "complete", thermalSource: "fortyguard_live" }),
    ).toBe("FORTYGUARD LIVE");
    expect(
      sourceBannerLabel({
        status: "complete",
        thermalSource: "fortyguard_cached",
      }),
    ).toBe("FORTYGUARD CACHED");
    expect(sourceBannerLabel({ status: "complete", thermalSource: "replay" })).toBe(
      "REPLAY",
    );
  });

  it("labels PARTIAL from job status or data status", () => {
    expect(sourceBannerLabel({ status: "partial" })).toBe("PARTIAL");
    expect(
      sourceBannerLabel({ status: "complete", dataStatus: "partial" }),
    ).toBe("PARTIAL");
  });

  it("does not label queued jobs as live", () => {
    expect(sourceBannerLabel({ status: "queued" })).toBe("UNAVAILABLE");
  });
});
