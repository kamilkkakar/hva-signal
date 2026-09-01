import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { BubbleExplorer, bubbleTooltipLines, presentBubbleExplorer } from "./BubbleExplorer";
import type { CrossCityAreaRecord } from "./types";

const records: CrossCityAreaRecord[] = [
  {
    cityId: "phoenix-az",
    cityLabel: "Phoenix, AZ",
    areaId: "phx-1",
    areaLabel: "Comparison Area 1",
    metrics: {
      selectedTimeTemperatureC: 40.1,
      medianHouseholdIncomeUsd: 55_000,
      population: 100_000,
      treeCanopyPct: 10.2,
      olderHousingPct: 42,
    },
  },
  {
    cityId: "las-vegas-nv",
    cityLabel: "Las Vegas, NV",
    areaId: "vegas-1",
    areaLabel: "Comparison Area 2",
    metrics: {
      selectedTimeTemperatureC: 43.4,
      medianHouseholdIncomeUsd: 61_000,
      population: 220_000,
      treeCanopyPct: null,
      olderHousingPct: 50,
    },
  },
  {
    cityId: "tucson-az",
    cityLabel: "Tucson, AZ",
    areaId: "tuc-1",
    areaLabel: "Comparison Area 3",
    metrics: {
      selectedTimeTemperatureC: null,
      medianHouseholdIncomeUsd: 49_000,
      population: 120_000,
      treeCanopyPct: 7.5,
      olderHousingPct: 60,
    },
  },
];

describe("cross-city bubble explorer", () => {
  it("omits rows missing an axis value and discloses the omitted count", () => {
    const view = presentBubbleExplorer(
      records,
      ["phoenix-az", "las-vegas-nv", "tucson-az"],
      "phoenix-az",
    );
    expect(view.filteredCount).toBe(3);
    // Default axes are canopy × temperature; vegas missing canopy, tucson missing temp.
    expect(view.plotted).toHaveLength(1);
    expect(view.omittedCount).toBe(2);
    expect(view.plotted.map((point) => point.areaId)).toEqual(["phx-1"]);
  });

  it("keeps plotted bubbles inside the chart axes rather than on top of them", () => {
    const view = presentBubbleExplorer(
      records,
      ["phoenix-az", "las-vegas-nv"],
      "phoenix-az",
      {
        x: "medianHouseholdIncomeUsd",
        y: "selectedTimeTemperatureC",
        size: "population",
        fill: "treeCanopyPct",
      },
    );
    expect(view.plotted.length).toBeGreaterThan(1);
    for (const point of view.plotted) {
      expect(point.cx - point.radius).toBeGreaterThan(108);
      expect(point.cy - point.radius).toBeGreaterThan(28);
      expect(point.cy + point.radius).toBeLessThan(296);
    }
  });

  it("marks missing fill in the tooltip disclosure", () => {
    expect(bubbleTooltipLines(records[1] ?? records[0])).toContain(
      "Tree canopy fill not published for this area.",
    );
  });

  it("uses focused city scale when exactly one city is isolated", () => {
    const focused = presentBubbleExplorer(records, ["phoenix-az"], "phoenix-az");
    expect(focused.scaleMode).toBe("focused");
    const comparison = presentBubbleExplorer(records, ["phoenix-az"], "phoenix-az", undefined, {
      forceComparisonScale: true,
    });
    expect(comparison.scaleMode).toBe("comparison");
  });

  it("renders the explorer copy without causal wording and with explicit axes", () => {
    const html = renderToStaticMarkup(
      createElement(BubbleExplorer, {
        records,
        activeCityIds: ["phoenix-az", "las-vegas-nv", "tucson-az"],
        selectedCityId: "las-vegas-nv",
      }),
    );

    expect(html).toContain("Tree canopy (%)");
    expect(html).toContain("Selected-time temperature (°C)");
    expect(html).toContain('data-testid="cross-city-omitted"');
    expect(html).toContain('data-testid="bubble-x-axis"');
    expect(html).toContain('data-testid="bubble-y-axis"');
    expect(html.toLowerCase()).not.toContain("causes");
    expect(html.toLowerCase()).not.toContain("drives heat");
  });

  it("keeps city hue in fill rather than a universal palette", () => {
    const view = presentBubbleExplorer(records, ["phoenix-az", "las-vegas-nv"], "phoenix-az");
    const phoenix = view.plotted.find((point) => point.cityId === "phoenix-az");
    expect(phoenix?.fill).toMatch(/^oklch\(/);
    expect(phoenix?.fill).toContain("250");
  });
});
