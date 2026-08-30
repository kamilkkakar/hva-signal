import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { composeSelectedAreaStory, SelectedAreaStoryPanel } from "@/features/selectedAreaStory";
import { AREA_1, contextView, documentFor, sufficientResult } from "@/features/selectedAreaStory/fixtures";
import { MAP_MODE_META } from "@/features/selectedAreaStory/copy";
import { isPublicContextEnabled } from "./publicContextGate";
import { AreaContextList } from "./AreaContextList";
import { MapModeTabs } from "./MapModeTabs";
import { presentList } from "./present";
import type { MapMode } from "./types";

const here = path.dirname(fileURLToPath(import.meta.url));

function firstRead(html: string): string {
  return html.replace(/<details\b[^>]*>[\s\S]*?<\/details>/gi, "");
}

describe("V2-N context chrome", () => {
  it("defaults public context on and can be disabled", () => {
    expect(isPublicContextEnabled()).toBe(true);
    expect(isPublicContextEnabled("0")).toBe(false);
  });

  it("shows Analysis Area N and 4-6 facts, with GEOID only in closed details", () => {
    const story = composeSelectedAreaStory({
      selectedGeoid: AREA_1,
      result: sufficientResult(),
      context: contextView(),
      document: documentFor(contextView()),
    });
    expect(story.questions.different.facts.length).toBeGreaterThanOrEqual(4);
    expect(story.questions.different.facts.length).toBeLessThanOrEqual(6);
    const html = renderToStaticMarkup(
      createElement(SelectedAreaStoryPanel, { story, mode: "TREE_CANOPY" }),
    );
    const visible = firstRead(html);
    expect(visible).toContain("Analysis Area 1");
    expect(visible).toContain("WHAT ARE THERMAL CONDITIONS HERE?");
    expect(visible).toContain("WHAT MAKES THIS AREA DIFFERENT?");
    expect(visible).not.toContain(AREA_1);
    expect(visible).not.toMatch(/\bGEOID\b/);
    expect(visible).not.toContain("NOT_IDENTIFIED_IN_DATASET");
    expect(visible).not.toContain("THERMAL=");
    expect(visible).not.toMatch(/no cooling site/i);
    expect(visible).not.toContain("THERMAL EVIDENCE: UNKNOWN");
    expect(html).toContain(AREA_1);
    expect(html).not.toMatch(/<details[^>]*\sopen[\s>]/);
    const factsBlock = html.match(/data-testid="story-facts"[^>]*>([\s\S]*?)<\/ul>/)?.[1] ?? "";
    const factItems = factsBlock.match(/<li /g) ?? [];
    expect(factItems.length).toBeGreaterThanOrEqual(4);
    expect(factItems.length).toBeLessThanOrEqual(6);
  });

  it("keeps the 25-row inventory table behind closed details", () => {
    const html = renderToStaticMarkup(
      createElement(AreaContextList, {
        rows: presentList(documentFor(contextView())),
        mode: "INCOME",
      }),
    );
    const visible = firstRead(html);
    expect(html).toContain('data-testid="area-context-inventory"');
    expect(html).not.toMatch(/<details[^>]*\sopen[\s>]/);
    expect(visible).not.toContain(AREA_1);
    expect(visible).not.toContain("NOT_IDENTIFIED_IN_DATASET");
    expect(visible).not.toContain("THERMAL=");
    expect(html).toContain("Analysis Area 1");
  });

  it("keeps context map-mode legends off FortyGuard historical-position chrome", () => {
    for (const mode of ["TREE_CANOPY", "INCOME", "OLDER_HOUSING"] as MapMode[]) {
      const html = renderToStaticMarkup(
        createElement(MapModeTabs, { mode, onModeChange: () => undefined }),
      );
      expect(html).toContain('data-source-family="context"');
      expect(html).not.toMatch(/fortyguard/i);
      expect(html).not.toMatch(/historical position/i);
      expect(html).not.toMatch(/hatch/i);
      const meta = MAP_MODE_META.find((row) => row.mode === mode);
      expect(meta?.source).not.toMatch(/fortyguard/i);
      expect(meta?.meaning).toMatch(/plantable ground|median household income|built before 1980/i);
    }
    const thermal = renderToStaticMarkup(
      createElement(MapModeTabs, { mode: "THERMAL", onModeChange: () => undefined }),
    );
    expect(thermal).toContain('data-source-family="fortyguard"');
  });

  it("does not add a second Signal B map on the context band", () => {
    const band = readFileSync(path.join(here, "AreaContextBand.tsx"), "utf8");
    const shell = readFileSync(
      path.join(here, "../judgeShell/JudgeShell.tsx"),
      "utf8",
    );
    expect(band).not.toContain("SignalBMapStage");
    expect(band).not.toContain("JudgeMap");
    expect(shell.indexOf("<MapBand")).toBeLessThan(shell.indexOf("<RunBand"));
    expect((shell.match(/<MapBand/g) ?? []).length).toBe(1);
  });
});
