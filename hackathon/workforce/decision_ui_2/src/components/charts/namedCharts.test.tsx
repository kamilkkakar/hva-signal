import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  CumulativeAnomaly,
  HourlyCurve,
  MonthlyTrend,
  PersistenceChart,
  SeasonalComparison,
  TreatedVsComparison,
  YearOverYear,
} from "./index";

const CHARTS = [
  ["hourly_curve", HourlyCurve],
  ["monthly_trend", MonthlyTrend],
  ["seasonal_comparison", SeasonalComparison],
  ["year_over_year", YearOverYear],
  ["cumulative_anomaly", CumulativeAnomaly],
  ["persistence", PersistenceChart],
  ["treated_vs_comparison", TreatedVsComparison],
] as const;

describe("named temporal charts", () => {
  it("each chart type ships with chrome and a pending public series", () => {
    for (const [kind, Component] of CHARTS) {
      const { unmount } = render(<Component selectedAreaId={null} />);
      const frame = document.querySelector(`[data-testid="chart-${kind}"]`);
      expect(frame?.textContent).toMatch(/Unit/);
      expect(frame?.textContent).toMatch(/Period not bound/);
      expect(document.querySelector("[data-testid='empty-plot']")).toBeTruthy();
      unmount();
    }
  });
});
