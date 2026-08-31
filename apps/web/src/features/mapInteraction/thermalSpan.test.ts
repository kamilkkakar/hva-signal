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

  it("uses local contrast fill when the observed spread is narrow", () => {
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
    expect(encoded).toContain("33.5");
    expect(encoded).toContain("#b8c4a8");
    expect(encoded).toContain("#4e5648");
    expect(encoded).not.toContain("backend_order");
  });
});
