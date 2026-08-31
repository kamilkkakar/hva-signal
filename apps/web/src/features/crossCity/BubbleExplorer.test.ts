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
    areaLabel: "Phoenix Area 1",
    metrics: {
      selectedTimeTemperatureC: 40.1,
      medianHouseholdIncomeUsd: 55_000,
      population: 100_000,
      treeCanopyPct: 10.2,
    },
  },
  {
    cityId: "las-vegas-nv",
    cityLabel: "Las Vegas, NV",
    areaId: "vegas-1",
    areaLabel: "Las Vegas Area 1",
    metrics: {
      selectedTimeTemperatureC: 43.4,
      medianHouseholdIncomeUsd: 61_000,
      population: 220_000,
      treeCanopyPct: null,
    },
  },
  {
    cityId: "tucson-az",
    cityLabel: "Tucson, AZ",
    areaId: "tuc-1",
    areaLabel: "Tucson Area 1",
    metrics: {
      selectedTimeTemperatureC: null,
      medianHouseholdIncomeUsd: 49_000,
      population: 120_000,
      treeCanopyPct: 7.5,
    },
  },
];

describe("cross-city bubble explorer", () => {
  it("omits rows missing an axis value and discloses the omitted count", () => {
    const view = presentBubbleExplorer(records, ["phoenix-az", "las-vegas-nv", "tucson-az"], "phoenix-az");
    expect(view.filteredCount).toBe(3);
    expect(view.plotted).toHaveLength(2);
    expect(view.omittedCount).toBe(1);
    expect(view.plotted.map((point) => point.areaId)).toEqual(["phx-1", "vegas-1"]);
  });

  it("marks missing fill in the tooltip disclosure", () => {
    expect(bubbleTooltipLines(records[1] ?? records[0])).toContain(
      "Tree canopy fill not published for this area.",
    );
  });

  it("renders the explorer copy without causal wording", () => {
    const html = renderToStaticMarkup(
      createElement(BubbleExplorer, {
        records,
        activeCityIds: ["phoenix-az", "las-vegas-nv", "tucson-az"],
        selectedCityId: "las-vegas-nv",
      }),
    );

    expect(html).toContain("Selected-time temperature (°C)");
    expect(html).toContain("Median household income");
    expect(html).toContain("Tree canopy fill not published for this area.");
    expect(html).toContain('data-testid="cross-city-omitted"');
    expect(html.toLowerCase()).not.toContain("causes");
    expect(html.toLowerCase()).not.toContain("drives heat");
  });
});
