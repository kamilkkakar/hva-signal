import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  bindHistoricalPositions,
  finiteUnitInterval,
  formatComparisonFrame,
  formatExactPosition,
} from "./bind";
import { clusteredResult, separatedResult } from "./fixtures";

const here = path.dirname(fileURLToPath(import.meta.url));

describe("bindHistoricalPositions", () => {
  it("reads existing q_A on the 0–1 scale and does not invent marks", () => {
    const clustered = bindHistoricalPositions({ result: clusteredResult() });
    const separated = bindHistoricalPositions({ result: separatedResult() });
    expect(clustered.marks).toHaveLength(25);
    expect(separated.marks).toHaveLength(25);
    expect(clustered.comparison).toBe("withheld");
    expect(separated.comparison).toBe("supported");
    expect(Math.max(...clustered.marks.map((mark) => mark.position))).toBeLessThan(0.22);
    expect(Math.max(...separated.marks.map((mark) => mark.position))).toBeGreaterThan(0.9);
  });

  it("drops out-of-range or missing q_A instead of clamping", () => {
    expect(finiteUnitInterval(1.2)).toBeNull();
    expect(finiteUnitInterval(-0.01)).toBeNull();
    expect(finiteUnitInterval(Number.NaN)).toBeNull();
    const bound = bindHistoricalPositions({
      result: {
        thermal_differentiation_state: "SUFFICIENT",
        zones: [
          { zone_id: "a", q_A: 0.4 },
          { zone_id: "b", q_A: 1.4 },
          { zone_id: "c" },
        ],
      },
    });
    expect(bound.marks).toEqual([{ zoneId: "a", position: 0.4 }]);
  });

  it("formats exact position without percent and frames years without long IDs", () => {
    expect(formatExactPosition(0.2)).toBe("0.200");
    expect(formatComparisonFrame([2022, 2023, 2024], "03:00")).toBe(
      "03:00 · 2022–2024 same hour",
    );
    expect(formatComparisonFrame(null, "03:00")).toBeNull();
    expect(formatComparisonFrame([2022], null)).toBeNull();
  });

  it("does not compute q_A, S, or a new floor", () => {
    const source = readFileSync(path.join(here, "bind.ts"), "utf8");
    expect(source).not.toContain("midrank");
    expect(source).not.toMatch(/\bECDF\b/);
    expect(source).not.toContain("0.10");
    expect(source).not.toMatch(/observed_spread\s*[<>=]/);
    expect(source).not.toMatch(/q_A\s*\*/);
  });
});
