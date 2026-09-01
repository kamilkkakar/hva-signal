import { describe, expect, it } from "vitest";
import { snapshotCatalog } from "./fixtures";
import { highlightFillPaint } from "./highlight";
import { initialInteractionState } from "./state";
import { observedThermalSpan } from "./thermalSpan";

describe("observedThermalSpan", () => {
  it("reads zone-mean span from selected-time snapshot catalogs", () => {
    const catalog = snapshotCatalog();
    const span = observedThermalSpan(catalog);
    expect(span).not.toBeNull();
    expect(span?.zoneCount).toBe(5);
    expect(span?.spreadC).toBeGreaterThan(0);
  });

  it("keeps fixed THERMAL_DISPLAY_SCALE_V1 by default even when spread is narrow", () => {
    const catalog = snapshotCatalog();
    catalog.collection.features.forEach((feature, index) => {
      feature.properties.mean_temperature_c = 33.5 + index * 0.04;
    });
    const span = observedThermalSpan(catalog);
    expect(span?.spreadC).toBeLessThan(2);
    const fill = highlightFillPaint(catalog, {
      ...initialInteractionState(),
      layerActive: true,
    });
    const encoded = JSON.stringify(fill["fill-color"]);
    expect(encoded).toContain("15");
    expect(encoded).toContain("60");
    expect(encoded).not.toContain("33.5");
    expect(encoded).not.toContain("backend_order");
  });

  it("does not AOI-stretch absolute temperature even when a legacy enhance flag is supplied", () => {
    const catalog = snapshotCatalog();
    catalog.collection.features.forEach((feature, index) => {
      feature.properties.mean_temperature_c = 33.5 + index * 0.04;
    });
    const fill = highlightFillPaint(
      catalog,
      { ...initialInteractionState(), layerActive: true },
      { enhanceLocalContrast: true },
    );
    const encoded = JSON.stringify(fill["fill-color"]);
    expect(encoded).toContain("15");
    expect(encoded).toContain("60");
    expect(encoded).not.toContain("33.5");
  });
});
