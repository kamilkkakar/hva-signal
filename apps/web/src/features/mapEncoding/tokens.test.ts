import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { blendOnto, contrastRatio } from "./contrast";
import {
  CURRENT_AOI_AUTOSTRETCH,
  FORBIDDEN_LEGEND_PHRASES,
  LEGEND_AXIS,
  LEGEND_DENIAL,
  LEGEND_HIGH_LABEL,
  LEGEND_INSUFFICIENT,
  LEGEND_LOW_LABEL,
  PERCENTILE_AUTOSTRETCH,
  RANK_FOR_B,
  SIGNAL_A_FILL_OPACITY,
  SIGNAL_A_HALO,
  SIGNAL_A_INK,
  SIGNAL_A_PANEL,
  SIGNAL_A_PAPER,
  SIGNAL_A_POS_HIGH,
  SIGNAL_A_POS_LOW,
  SIGNAL_A_POS_STOPS,
  SIGNAL_B_HOLD_ENCODING,
  SIGNAL_B_HOLD_FILL,
  SIGNAL_B_PUBLIC,
} from "./tokens";

describe("historical position tokens", () => {
  it("locks the C2b sequential and the required legend axis", () => {
    expect([...SIGNAL_A_POS_STOPS]).toEqual([
      "#8a9278",
      "#6c7462",
      "#4e5648",
      "#32382e",
      "#161a14",
    ]);
    expect(LEGEND_LOW_LABEL).toBe("LOWER HISTORICAL POSITION");
    expect(LEGEND_HIGH_LABEL).toBe("HIGHER HISTORICAL POSITION");
    expect(LEGEND_AXIS).toBe(
      "LOWER HISTORICAL POSITION ↔ HIGHER HISTORICAL POSITION",
    );
  });

  it("meets WCAG text contrast and a luminance-ordered ramp", () => {
    expect(contrastRatio(SIGNAL_A_INK, SIGNAL_A_PANEL)).toBeGreaterThanOrEqual(12);
    expect(contrastRatio(SIGNAL_A_POS_LOW, SIGNAL_A_POS_HIGH)).toBeGreaterThanOrEqual(
      5,
    );
    expect(contrastRatio(SIGNAL_A_POS_LOW, SIGNAL_A_PAPER)).toBeGreaterThanOrEqual(
      1.8,
    );
    const effectiveLow = blendOnto(
      SIGNAL_A_POS_LOW,
      SIGNAL_A_PAPER,
      SIGNAL_A_FILL_OPACITY,
    );
    expect(contrastRatio(effectiveLow, SIGNAL_A_PAPER)).toBeGreaterThanOrEqual(1.6);
    expect(contrastRatio(SIGNAL_A_HALO, SIGNAL_A_POS_HIGH)).toBeGreaterThanOrEqual(12);
    for (let index = 1; index < SIGNAL_A_POS_STOPS.length; index += 1) {
      expect(
        contrastRatio(SIGNAL_A_POS_STOPS[index - 1], SIGNAL_A_POS_STOPS[index]),
      ).toBeGreaterThanOrEqual(1.35);
    }
  });

  it("holds B as neutral numeric and freezes stretch off", () => {
    expect(SIGNAL_B_PUBLIC).toBe(false);
    expect(SIGNAL_B_HOLD_ENCODING).toBe("neutral_numeric_hold");
    expect(SIGNAL_B_HOLD_FILL).toBe("#9aa392");
    expect(CURRENT_AOI_AUTOSTRETCH).toBe(false);
    expect(PERCENTILE_AUTOSTRETCH).toBe(false);
    expect(RANK_FOR_B).toBe(false);
  });

  it("keeps legend copy off the forbidden axis words", () => {
    const blob = [LEGEND_AXIS, LEGEND_DENIAL, LEGEND_INSUFFICIENT]
      .join("\n")
      .toLowerCase();
    for (const phrase of FORBIDDEN_LEGEND_PHRASES) {
      expect(blob).not.toContain(phrase);
    }
  });

  it("does not ship the rejected phosphor-filament endpoints in tokens", () => {
    const source = readFileSync(
      join(dirname(fileURLToPath(import.meta.url)), "tokens.ts"),
      "utf8",
    );
    expect(source).not.toContain("#2f8f78");
    expect(source).not.toContain("#d56a1c");
  });
});
