import { describe, expect, it } from "vitest";
import { SIGNAL_A_HATCH_LOW_ID, SIGNAL_A_INSUFFICIENT_FILL } from "./tokens";
import {
  signalAColorStops,
  signalAFillPaint,
  signalAHaloPaint,
  signalAHatchPaint,
  signalALinePaint,
} from "./paint";

describe("signal A position paint", () => {
  it("interpolates authorized order only, never q_A or °C", () => {
    const fill = signalAFillPaint({ authorized: true, maxOrder: 25 });
    const serialized = JSON.stringify(fill);
    expect(fill["fill-opacity"]).toBeGreaterThan(0);
    expect(serialized).toContain("interpolate");
    expect(serialized).toContain("backend_order");
    expect(serialized).toContain("#8a9278");
    expect(serialized).toContain("#161a14");
    expect(serialized).not.toContain("q_A");
    expect(serialized).not.toContain("mean_temperature");
    expect(serialized).not.toContain("temperature_min");
    expect(serialized).not.toContain("#2f8f78");
    expect(serialized).not.toContain("#d56a1c");
    expect(signalAColorStops(25)[0]).toBe(1);
    expect(signalAColorStops(25).at(-2)).toBe(25);
  });

  it("drops the sequential when position is withheld", () => {
    const fill = signalAFillPaint({ authorized: false, maxOrder: 25 });
    const hatch = signalAHatchPaint({ authorized: false, maxOrder: 25 });
    const line = signalALinePaint(false);
    const halo = signalAHaloPaint(false);
    expect(fill["fill-color"]).toBe(SIGNAL_A_INSUFFICIENT_FILL);
    expect(fill["fill-opacity"]).toBe(0);
    expect(JSON.stringify(fill)).not.toContain("interpolate");
    expect(JSON.stringify(fill)).not.toContain("#8a9278");
    expect(hatch["fill-opacity"]).toBe(0);
    expect(hatch["fill-pattern"]).toBe(SIGNAL_A_HATCH_LOW_ID);
    expect(line["line-color"]).toBe("#4e5748");
    expect(halo["line-opacity"]).toBe(0);
  });

  it("pairs authorized fills with hatch density on order tertiles", () => {
    const hatch = signalAHatchPaint({ authorized: true, maxOrder: 25 });
    const serialized = JSON.stringify(hatch);
    expect(hatch["fill-opacity"]).toBeGreaterThan(0);
    expect(serialized).toContain("step");
    expect(serialized).toContain("hva-pos-hatch-low");
    expect(serialized).toContain("hva-pos-hatch-high");
    expect(serialized).not.toContain("q_A");
  });
});
