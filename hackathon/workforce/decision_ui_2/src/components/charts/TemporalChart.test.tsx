import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CHART_KINDS } from "@/contracts";
import { publicChart } from "@/data/publicSurface";
import { TEST_ONLY_HOURLY } from "@/fixtures/temporal.fixture";
import { TemporalChart } from "./TemporalChart";

describe("temporal charts", () => {
  it("requires chrome and stays empty on the public contract", () => {
    for (const kind of CHART_KINDS) {
      const { unmount } = render(
        <TemporalChart model={publicChart(kind)} selectedAreaId="area-2" />,
      );
      const frame = screen.getByTestId(`chart-${kind}`);
      expect(frame.textContent).toMatch(/Unit/);
      expect(frame.textContent).toMatch(/Period/);
      expect(frame.textContent).toMatch(/Baseline/);
      expect(frame.textContent).toMatch(/Coverage/);
      expect(frame.textContent).toMatch(/Source/);
      expect(frame.textContent).toContain("Analysis area 2");
      expect(screen.getByTestId("empty-plot")).toBeTruthy();
      unmount();
    }
  });

  it("plots TEST_ONLY series only when a fixture is passed in", () => {
    render(<TemporalChart model={TEST_ONLY_HOURLY} selectedAreaId={null} />);
    expect(screen.getByRole("img").getAttribute("aria-label")).toContain("°C");
    expect(document.querySelector("polyline")).toBeTruthy();
  });
});
