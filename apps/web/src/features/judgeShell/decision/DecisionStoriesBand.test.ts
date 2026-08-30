import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { DecisionStoriesBand } from "./DecisionStoriesBand";
import { ObservedInstantsChart } from "./ObservedInstantsChart";
import { MatchedNighttimePanel } from "./MatchedNighttimePanel";
import { MATCHED_TITLE, INSTANTS_TITLE, INSTANTS_GAP, VERIFY_MATURITY } from "./copy";

const here = path.dirname(fileURLToPath(import.meta.url));

describe("decision stories production mount", () => {
  it("does not import workforce Decision UI fixtures in production modules", () => {
    const files = readdirSync(here).filter(
      (name) =>
        (name.endsWith(".ts") || name.endsWith(".tsx")) &&
        !name.includes(".test."),
    );
    for (const name of files) {
      const source = readFileSync(path.join(here, name), "utf8");
      expect(source.includes("TEST_" + "ONLY")).toBe(false);
      expect(source).not.toContain("decision_ui_2");
      expect(source).not.toContain("workforce/");
    }
  });

  it("renders unknown until an analysis area is selected", () => {
    const html = renderToStaticMarkup(createElement(DecisionStoriesBand, { selectedZoneId: null }));
    expect(html).toContain("UNKNOWN");
    expect(html).toContain(MATCHED_TITLE);
    expect(html).toContain(INSTANTS_TITLE);
    expect(html).toContain(VERIFY_MATURITY.replace(/&/g, "&amp;"));
    expect(html).toContain("INSUFFICIENT EVIDENCE");
    expect(html.includes("TEST_" + "ONLY")).toBe(false);
  });

  it("draws four discrete markers with explicit unobserved gaps", () => {
    const html = renderToStaticMarkup(
      createElement(ObservedInstantsChart, {
        view: {
          status: "AVAILABLE",
          reason: null,
          instants: [
            { instantId: "03:00_D", label: "03:00 D", date: "2024-07-08", localTime: "03:00", temperatureC: 34.52, activityId: null },
            { instantId: "15:00", label: "15:00", date: "2024-07-08", localTime: "15:00", temperatureC: 42.328, activityId: "92086c4c-1550-4263-8ac8-9a6c9e030bc4" },
            { instantId: "21:00", label: "21:00", date: "2024-07-08", localTime: "21:00", temperatureC: 39.256, activityId: "9865bd33-43a0-42b0-bc9b-74b27510002d" },
            { instantId: "03:00_D+1", label: "03:00 D+1", date: "2024-07-09", localTime: "03:00", temperatureC: 34.676, activityId: null },
          ],
          differences: [
            { fromId: "03:00_D", toId: "15:00", deltaC: 7.808 },
            { fromId: "15:00", toId: "21:00", deltaC: -3.072 },
            { fromId: "21:00", toId: "03:00_D+1", deltaC: -4.581 },
          ],
        },
      }),
    );
    expect(html).toContain(INSTANTS_GAP);
    expect(html).toContain('data-autostretch="false"');
    expect(html).toContain("03:00 D");
    expect(html).toContain("03:00 D+1");
    expect(html).toContain("Not an hourly series");
    expect(html).not.toContain("q_A");
    expect(html).not.toContain("cooling rate");
  });

  it("shows matched-window years and nights without a YoY choropleth", () => {
    const html = renderToStaticMarkup(
      createElement(MatchedNighttimePanel, {
        view: {
          status: "AVAILABLE",
          reason: null,
          years: [
            { year: "2022", meanC: 32.8 },
            { year: "2023", meanC: 33.81 },
            { year: "2024", meanC: 34.33 },
          ],
          change2024vs2022: 1.54,
          medianChange: 1.53,
          nightsWarmer: 22,
          nightsTotal: 31,
        },
      }),
    );
    expect(html).toContain("2022");
    expect(html).toContain("2024 vs 2022");
    expect(html).toContain("25-area median");
    expect(html).toContain("22 / 31");
    expect(html).not.toContain("choropleth");
    expect(html).not.toContain("JJA");
    expect(html).not.toContain("HeatDose");
  });
});
