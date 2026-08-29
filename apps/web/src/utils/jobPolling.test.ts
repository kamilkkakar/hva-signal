import { describe, expect, it } from "vitest";
import {
  MAX_UNCHANGED_IN_FLIGHT_POLLS,
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
    expect(shouldContinuePolling(null)).toBe(false);
  });

  it("stops after unchanged in-flight polls so a queued stub cannot poll forever", () => {
    let stall = 0;
    let previous: "queued" | null = "queued";
    expect(shouldKeepPolling("queued", stall)).toBe(true);

    for (let i = 0; i < MAX_UNCHANGED_IN_FLIGHT_POLLS; i += 1) {
      stall = nextStallCount("queued", previous, stall);
      previous = "queued";
    }

    expect(stall).toBe(MAX_UNCHANGED_IN_FLIGHT_POLLS);
    expect(shouldKeepPolling("queued", stall)).toBe(false);
  });

  it("resets stall when status advances", () => {
    const stall = nextStallCount("fetching_thermal", "queued", 3);
    expect(stall).toBe(0);
    expect(shouldKeepPolling("fetching_thermal", stall)).toBe(true);
  });
});
