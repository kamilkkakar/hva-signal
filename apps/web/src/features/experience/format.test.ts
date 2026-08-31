import { describe, expect, it } from "vitest";
import { formatDeltaC, formatLocalObservation, formatTempC } from "./format";

describe("experience formatters", () => {
  it("formats a bound local clock without hard-coded dates", () => {
    expect(formatLocalObservation("2025-07-15 03:00")).toBe(
      "15 Jul 2025 · 03:00 local",
    );
    expect(formatLocalObservation("2022-06-30T03:00")).toBe(
      "30 Jun 2022 · 03:00 local",
    );
  });

  it("formats bound temperatures and deltas", () => {
    expect(formatTempC(33.7)).toBe("33.7 °C");
    expect(formatDeltaC(1.5)).toBe("+1.50 °C");
    expect(formatDeltaC(-0.4)).toBe("-0.40 °C");
  });
});
