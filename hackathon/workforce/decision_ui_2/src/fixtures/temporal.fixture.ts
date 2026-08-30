/** TEST_ONLY fixture. Not imported by production routes. */
import type { GroupedSeries, TemporalSeries } from "@/contracts";
import { AVAILABILITY } from "@/contracts";
import { TEST_ONLY } from "./TEST_ONLY";

export const TEST_ONLY_HOURLY: TemporalSeries & { readonly __testOnly: typeof TEST_ONLY } = {
  __testOnly: TEST_ONLY,
  kind: "hourly_curve",
  chrome: {
    title: "24-hour curve",
    unit: "°C",
    period: "One dated local day",
    baseline: "Same-area daily mean",
    coverage: "24 / 24 hours",
    source: "TEST_ONLY fixture",
  },
  points: {
    availability: AVAILABILITY.READY,
    value: [
      { x: "00", y: 28.1 },
      { x: "03", y: 26.4 },
      { x: "06", y: 27.0 },
      { x: "09", y: 31.2 },
      { x: "12", y: 36.8 },
      { x: "15", y: 38.1 },
      { x: "18", y: 34.4 },
      { x: "21", y: 30.2 },
    ],
  },
};

export const TEST_ONLY_TREATED: GroupedSeries & { readonly __testOnly: typeof TEST_ONLY } = {
  __testOnly: TEST_ONLY,
  kind: "treated_vs_comparison",
  chrome: {
    title: "Treated vs comparison",
    unit: "°C",
    period: "Named post-treatment window",
    baseline: "Named pre-treatment window",
    coverage: "Coverage not claimed",
    source: "TEST_ONLY fixture",
  },
  groups: {
    availability: AVAILABILITY.READY,
    value: [
      {
        id: "treated",
        label: "Treated analysis areas",
        points: [
          { x: "before", y: 29.4 },
          { x: "after", y: 28.9 },
        ],
      },
      {
        id: "comparison",
        label: "Comparison analysis areas",
        points: [
          { x: "before", y: 29.1 },
          { x: "after", y: 29.2 },
        ],
      },
    ],
  },
};
