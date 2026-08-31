import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { MapInteractionChrome } from "@/features/mapInteraction/MapInteractionChrome";
import { presentMapInteraction } from "@/features/mapInteraction/present";
import { initialInteractionState } from "@/features/mapInteraction/state";
import { snapshotCatalog } from "@/features/mapInteraction/fixtures";
import { ThermalHero } from "./ThermalHero";
import { DecisionBrief } from "./DecisionBrief";
import { DecisionDirection } from "./DecisionDirection";
import { synthesizeNarrative } from "./narrative";
import { METRIC_CHANGE, METRIC_TEMP } from "./copy";

const here = path.dirname(fileURLToPath(import.meta.url));

describe("analytical story contract", () => {
  it("labels selected observation and 2024 vs 2022 matched change distinctly", () => {
    const html = renderToStaticMarkup(
      createElement(ThermalHero, {
        selectedZoneId: "04013107401",
        onSelect: () => undefined,
        temperatureC: 33.7,
        observationStamp: "2025-07-15 03:00 America/Phoenix",
        observationDateLabel: "15 Jul 2025 · 03:00",
        history: {
          status: "unavailable",
          sentence: "Historical position is not available for this observation.",
          reason: "reason",
          percent: null,
        },
        spatial: {
          status: "withheld",
          sentence: "Thermal differences across the analysis areas are too small.",
        },
        change2024vs2022: 1.54,
      }),
    );
    expect(html).toContain(METRIC_TEMP);
    expect(html).toContain(METRIC_CHANGE);
    expect(html).toContain("2024 vs 2022");
    expect(html).toContain("15 Jul 2025 · 03:00");
    expect(html).toContain('data-testid="hero-history"');
    expect(html).toContain('data-testid="hero-spatial"');
    expect(html).not.toMatch(/2025 vs 2022/i);
  });

  it("places evidence pattern on the top Decision Brief", () => {
    const synthesis = synthesizeNarrative({
      areaLabel: "Analysis Area 1",
      analysisAreaCount: 25,
      selectedTemperatureC: 33.7,
      observationStamp: "15 Jul 2025 · 03:00",
      spatialDiff: "INSUFFICIENT",
      historicalPosition: {
        status: "UNAVAILABLE",
        percent: null,
        sentence: "Historical position is not available for this observation.",
      },
      matchedChangeC: 1.54,
      geographyMedianChangeC: 1.53,
      matchedNightsTotal: 31,
      observedHighC: 42.3,
      observedHighLabel: "15:00",
      contextComparisons: [],
      preparedness: "NOT_IDENTIFIED_IN_DATASET",
      thermalAvailable: true,
    });
    const html = renderToStaticMarkup(
      createElement(DecisionBrief, {
        synthesis,
        areaLabel: "Analysis Area 1",
      }),
    );
    expect(html).toContain('data-testid="evidence-pattern"');
    expect(html).toContain('data-testid="evidence-summary"');
    expect(html).toContain("Highest observed instant");
  });

  it("renders direction from deterministic synthesis without scores", () => {
    const synthesis = synthesizeNarrative({
      areaLabel: "Analysis Area 1",
      analysisAreaCount: 25,
      selectedTemperatureC: 33.7,
      observationStamp: "15 Jul 2025 · 03:00",
      spatialDiff: "INSUFFICIENT",
      historicalPosition: {
        status: "UNAVAILABLE",
        percent: null,
        sentence: "Historical position is not available for this observation.",
      },
      matchedChangeC: 1.54,
      geographyMedianChangeC: 1.53,
      matchedNightsTotal: 31,
      observedHighC: 42.3,
      observedHighLabel: "15:00",
      contextComparisons: [],
      preparedness: "NOT_IDENTIFIED_IN_DATASET",
      thermalAvailable: true,
    });
    const html = renderToStaticMarkup(
      createElement(DecisionDirection, {
        synthesis,
        areaLabel: "Analysis Area 1",
      }),
    );
    expect(html).toContain("TEMPORAL_CHANGE_DOMINATES");
    expect(html).toContain("1.54 °C higher");
    expect(html).not.toMatch(/vulnerability score|priority score|warming trend|climate trend/i);
    expect(html).not.toMatch(/no row/i);
  });

  it("keeps thermal legend off context-quantity fill kinds", () => {
    const catalog = snapshotCatalog();
    catalog.fill_kind = "context_quantity";
    catalog.layer_title = "Tree canopy";
    catalog.meaning = "percent of plantable ground";
    const view = presentMapInteraction({
      enabled: true,
      catalog,
      state: { ...initialInteractionState(), layerActive: true },
    });
    const html = renderToStaticMarkup(
      createElement(MapInteractionChrome, {
        view,
        dispatch: () => undefined,
        catalogKind: catalog.kind,
        fillKind: catalog.fill_kind,
        layerTitle: catalog.layer_title,
        layerMeaning: catalog.meaning,
      }),
    );
    expect(html).toContain('data-testid="context-mode-legend"');
    expect(html).toContain("TREE_CANOPY");
    expect(html).not.toContain("thermal-snapshot-legend");
    expect(html).not.toMatch(/Selected-time temperature|25–45/i);
  });

  it("wires synthesis and Decision Brief into the judge shell", () => {
    const shell = readFileSync(path.join(here, "../judgeShell/JudgeShell.tsx"), "utf8");
    expect(shell).toContain("synthesizeNarrative");
    expect(shell).toContain("DecisionBrief");
    expect(shell).toContain("presentHistoricalPosition");
    expect(shell).toContain("presentSpatialDifferentiation");
  });
});
