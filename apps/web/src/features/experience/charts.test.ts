import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { presentMatched, presentObserved } from "@/features/judgeShell/decision/present";
import type { MatchedNighttimeView, ObservedSequenceView } from "@/features/judgeShell/decision/types";
import { INSTANTS_GAP, MATCHED_NOT_CLIMATE } from "./copy";
import { MatchedNightChart } from "./MatchedNightChart";
import { ObservedInstantsChart } from "./ObservedInstantsChart";

const GEOID = "04013107401";

const matchedDoc: MatchedNighttimeView = {
  selected_area: {
    mean_by_year: { "2022": 32.8, "2023": 33.9, "2024": 34.4 },
    change_2024_vs_2022: 1.6,
    matched_nights: 31,
    matched_nights_warmer: 22,
    matched_nights_cooler: 9,
  },
  analysis_geography: { median_change_2024_vs_2022: 1.53 },
};

const observedDoc: ObservedSequenceView = {
  observations: [
    { instant_id: "03:00_D", date: "2024-07-08", local_time: "03:00", temperature_c: 32.1, label: "03:00 D" },
    { instant_id: "15:00", date: "2024-07-08", local_time: "15:00", temperature_c: 41.2, label: "15:00" },
    { instant_id: "21:00", date: "2024-07-08", local_time: "21:00", temperature_c: 36.4, label: "21:00" },
    { instant_id: "03:00_D+1", date: "2024-07-09", local_time: "03:00", temperature_c: 31.8, label: "03:00 D+1" },
  ],
  direct_differences: [
    { from_instant_id: "03:00_D", to_instant_id: "15:00", delta_c: 9.1 },
    { from_instant_id: "15:00", to_instant_id: "21:00", delta_c: -4.8 },
    { from_instant_id: "21:00", to_instant_id: "03:00_D+1", delta_c: -4.6 },
  ],
};

describe("experience charts", () => {
  it("renders matched-night line+points from API fields only", () => {
    const view = presentMatched(GEOID, matchedDoc, null);
    const html = renderToStaticMarkup(
      createElement(MatchedNightChart, { view, areaLabel: "Analysis Area 1" }),
    );
    expect(html).toContain("Matched nighttime change");
    expect(html).toContain('data-viz="line-points"');
    expect(html).toContain("32.8 °C");
    expect(html).toContain("+1.60 °C");
    expect(html).toContain("Higher by 1.60 °C");
    expect(html).toContain("31 matched");
    expect(html).toContain(">°C<");
    expect(html).toContain(MATCHED_NOT_CLIMATE);
    expect(html).not.toContain("<rect");
    expect(html).not.toContain("climate trend");
    expect(html).not.toContain("warming trend");
    expect(html).not.toContain("q_A");
  });

  it("renders discrete observed instants with one interval note and observed high", () => {
    const view = presentObserved(GEOID, observedDoc, null);
    const html = renderToStaticMarkup(
      createElement(ObservedInstantsChart, { view, areaLabel: "Analysis Area 1" }),
    );
    expect(html).toContain(INSTANTS_GAP);
    expect(html).toContain("41.2 °C");
    expect(html).toContain("observed-high");
    expect(html).toContain("Gaps between observations");
    expect(html).toContain(">°C<");
    expect((html.match(/Interval not observed/g) ?? []).length).toBe(0);
    expect(html).not.toContain("24-HOUR CURVE");
    expect(html).not.toContain("cooling rate");
    expect(html).not.toContain("hourly series");
  });
});
