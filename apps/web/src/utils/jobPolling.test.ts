import { describe, expect, it } from "vitest";
import {
  MAX_CONSECUTIVE_NETWORK_ERRORS,
  MAX_IN_FLIGHT_OBSERVATION_MS,
  nextStallCount,
  shouldContinuePolling,
  shouldKeepPolling,
} from "./jobPolling";

describe("job polling", () => {
  it("polls in-flight statuses including queued", () => {
    expect(shouldContinuePolling("queued")).toBe(true);
    expect(shouldContinuePolling("computing")).toBe(true);
  });

  it("stops on unknown_job and terminal statuses", () => {
    expect(shouldContinuePolling("unknown_job")).toBe(false);
    expect(shouldContinuePolling("complete")).toBe(false);
    expect(shouldContinuePolling("failed")).toBe(false);
    expect(shouldContinuePolling("partial")).toBe(false);
    expect(shouldContinuePolling(null)).toBe(false);
  });

  it("keeps polling unchanged in-flight status", () => {
    let stall = 0;
    let previous: "queued" | null = "queued";
    for (let i = 0; i < 8; i += 1) {
      stall = nextStallCount("queued", previous, stall);
      previous = "queued";
      expect(shouldKeepPolling("queued", stall)).toBe(true);
    }
    expect(stall).toBe(8);
  });

  it("stops after the wall-clock observation horizon", () => {
    expect(
      shouldKeepPolling("queued", {
        elapsedMs: MAX_IN_FLIGHT_OBSERVATION_MS,
      }),
    ).toBe(false);
    expect(
      shouldKeepPolling("queued", {
        elapsedMs: MAX_IN_FLIGHT_OBSERVATION_MS - 1,
      }),
    ).toBe(true);
  });

  it("stops after consecutive network errors", () => {
    expect(
      shouldKeepPolling("queued", {
        consecutiveNetworkErrors: MAX_CONSECUTIVE_NETWORK_ERRORS,
      }),
    ).toBe(false);
  });

  it("resets stall count when status advances but still polls", () => {
    const stall = nextStallCount("fetching_thermal", "queued", 3);
    expect(stall).toBe(0);
    expect(shouldKeepPolling("fetching_thermal", stall)).toBe(true);
  });
});
