import { describe, expect, it } from "vitest";
import {
  ACTIVE_THERMAL_DISPLAY_SCALE,
  THERMAL_DISPLAY_SCALE_V1,
  THERMAL_DISPLAY_SCALE_VERSION,
  isOutsideThermalDomain,
  thermalObservedBandPosition,
  thermalScaleDomainLabel,
  thermalScaleTickLabels,
} from "./thermalDisplayScale";

describe("THERMAL_DISPLAY_SCALE_V1", () => {
  it("exists as a versioned multi-city policy", () => {
    expect(THERMAL_DISPLAY_SCALE_V1.version).toBe(THERMAL_DISPLAY_SCALE_VERSION);
    expect(ACTIVE_THERMAL_DISPLAY_SCALE).toBe(THERMAL_DISPLAY_SCALE_V1);
  });

  it("is not the Phoenix-only 25–45 envelope", () => {
    expect(THERMAL_DISPLAY_SCALE_V1.domainMin).toBeLessThan(25);
    expect(THERMAL_DISPLAY_SCALE_V1.domainMax).toBeGreaterThan(45);
    expect(THERMAL_DISPLAY_SCALE_V1.domainMin).toBe(15);
    expect(THERMAL_DISPLAY_SCALE_V1.domainMax).toBe(60);
  });

  it("does not enable request-local or percentile stretch", () => {
    expect(THERMAL_DISPLAY_SCALE_V1.currentAoiStretch).toBe(false);
    expect(THERMAL_DISPLAY_SCALE_V1.percentileStretch).toBe(false);
    expect(THERMAL_DISPLAY_SCALE_V1.localContrastDefault).toBe(false);
  });

  it("does not encode Phoenix / America/Phoenix / analysis-area identity", () => {
    const blob = JSON.stringify(THERMAL_DISPLAY_SCALE_V1).toLowerCase();
    expect(blob).not.toMatch(/phoenix|america\/phoenix|analysis area|geoid/);
  });

  it("uses end-cap overflow rather than AOI min/max stretch", () => {
    expect(THERMAL_DISPLAY_SCALE_V1.overflow).toBe("end_cap");
    expect(isOutsideThermalDomain(10)).toBe(true);
    expect(isOutsideThermalDomain(65)).toBe(true);
    expect(isOutsideThermalDomain(33.7)).toBe(false);
  });

  it("exposes separated tick labels with end-caps", () => {
    const ticks = thermalScaleTickLabels();
    expect(ticks.join(" ")).toMatch(/≤15/);
    expect(ticks.join(" ")).toMatch(/≥60/);
    expect(ticks.join("")).not.toBe("152535455560");
    expect(thermalScaleDomainLabel()).toContain("°C");
  });

  it("positions observed band within the fixed domain", () => {
    const band = thermalObservedBandPosition(33.5, 33.7);
    expect(band).not.toBeNull();
    expect(band!.leftPct).toBeGreaterThan(30);
    expect(band!.leftPct).toBeLessThan(50);
    expect(band!.widthPct).toBeGreaterThan(0);
  });
});
