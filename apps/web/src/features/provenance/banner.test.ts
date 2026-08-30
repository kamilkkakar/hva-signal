import { describe, expect, it } from "vitest";
import {
  refuseCollapsedSourceTape,
  SignalProvenanceError,
  signalProvenanceBanner,
} from "./banner";

describe("per-signal banner — live never beats cached", () => {
  it("labels cached B as CACHED", () => {
    expect(
      signalProvenanceBanner({
        source: "fortyguard_cached",
        dataStatus: "cached",
      }).banner,
    ).toBe("FORTYGUARD CACHED");
  });

  it("rejects cached source + live status instead of labeling LIVE", () => {
    expect(() =>
      signalProvenanceBanner({
        source: "fortyguard_cached",
        dataStatus: "live",
      }),
    ).toThrow(SignalProvenanceError);
    expect(() =>
      signalProvenanceBanner({
        source: "fortyguard_cached",
        dataStatus: "live",
      }),
    ).toThrow(/live does not beat cached/);
  });

  it("rejects live source + cached status instead of labeling LIVE", () => {
    expect(() =>
      signalProvenanceBanner({
        source: "fortyguard_live",
        dataStatus: "cached",
      }),
    ).toThrow(/live does not beat cached/);
  });

  it("rejects cached source labeled as replay", () => {
    expect(() =>
      signalProvenanceBanner({
        source: "fortyguard_cached",
        dataStatus: "replay",
      }),
    ).toThrow(/live does not beat cached/);
  });

  it("keeps partial on the cached path stem", () => {
    expect(
      signalProvenanceBanner({
        source: "fortyguard_cached",
        dataStatus: "partial",
      }),
    ).toEqual({ banner: "PARTIAL", pathStem: "FORTYGUARD CACHED" });
  });

  it("maps legal pairs only", () => {
    expect(
      signalProvenanceBanner({ source: "fortyguard_live", dataStatus: "live" })
        .banner,
    ).toBe("FORTYGUARD LIVE");
    expect(
      signalProvenanceBanner({ source: "replay", dataStatus: "replay" }).banner,
    ).toBe("REPLAY");
    expect(
      signalProvenanceBanner({
        source: "fortyguard_cached",
        dataStatus: "unavailable",
      }).banner,
    ).toBe("UNAVAILABLE");
  });

  it("refuses a single collapsed SourceTape", () => {
    expect(() => refuseCollapsedSourceTape()).toThrow(/never collapse/);
  });

  it("does not accept data_mode or job-level thermal_source", () => {
    const keys = Object.keys({
      source: "fortyguard_cached",
      dataStatus: "cached",
    });
    expect(keys).not.toContain("dataMode");
    expect(keys).not.toContain("thermalSource");
    expect(keys).not.toContain("status");
  });
});
