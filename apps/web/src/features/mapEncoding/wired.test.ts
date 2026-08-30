import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const root = dirname(fileURLToPath(import.meta.url));

function readFeature(relative: string): string {
  return readFileSync(join(root, "..", relative), "utf8");
}

describe("Judge map encoding wire", () => {
  it("paints C2b hatch on the mounted JudgeMap host, not only MapStage", () => {
    const highlight = readFeature("mapInteraction/highlight.ts");
    const stage = readFeature("mapInteraction/MapInteractionStage.tsx");
    const chrome = readFeature("mapInteraction/MapInteractionChrome.tsx");
    const band = readFeature("judgeShell/MapBand.tsx");
    const judgeMap = readFeature("judgeShell/map/JudgeMap.tsx");
    const mapStage = readFeature("map/MapStage.tsx");

    expect(highlight).toContain("signalAHatchPaint");
    expect(highlight).toContain("highlightHatchPaint");
    expect(stage).toContain("highlightHatchPaint");
    expect(stage).toContain("hva-map-interaction-hatch");
    expect(stage).toContain("allHatchImages");
    expect(chrome).toContain("HistoricalPositionLegend");
    expect(judgeMap).toContain("MapInteractionStage");
    expect(band).toContain("JudgeMap");
    expect(band).not.toContain("MapStage");

    expect(mapStage).toContain("signalAHatchPaint");
    expect(stage.split("highlightHatchPaint").length).toBeGreaterThan(2);
  });

  it("does not keep the rejected phosphor-filament or one-swatch tautology on JudgeMap", () => {
    const highlight = readFeature("mapInteraction/highlight.ts");
    const legend = readFeature("mapInteraction/legend.ts");
    const chrome = readFeature("mapInteraction/MapInteractionChrome.tsx");
    expect(highlight).not.toContain("#2f8f78");
    expect(highlight).not.toContain("#d56a1c");
    expect(legend).not.toMatch(/color encoding is the legend/i);
    expect(legend).not.toContain("#9aa392");
    expect(chrome).not.toMatch(/color encoding is the legend/i);
    expect(highlight).not.toMatch(/FORTYGUARD/);
  });
});
