import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { PUBLIC_STATUS } from "@/features/publicLanguage";
import { THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT } from "@/utils/mapLayer";
import { CapabilityExpansion } from "./capabilities/CapabilityExpansion";
import { ContextBar } from "./ContextBar";
import { CHIP_WINDOW, CHIP_WINDOW_ID } from "./copy";
import { HappeningBand } from "./HappeningBand";
import { happeningView } from "./happening";
import { ProvenanceBand } from "./ProvenanceBand";
import {
  INSUFFICIENT_HEADLINE,
  STAMP_SUPPORTED,
  STAMP_WITHHELD,
  SUFFICIENT_HEADLINE,
} from "./resultStory/copy";
import {
  ORACLE_S_INSUFFICIENT,
  ORACLE_S_SUFFICIENT,
  oracle0630Snapshot,
  oracle0701Snapshot,
} from "./resultStory/fixtures";
import { presentResultStory } from "./resultStory/presentation";
import { ResultStory } from "./resultStory/ResultStory";

const here = path.dirname(fileURLToPath(import.meta.url));

function firstRead(html: string): string {
  return html.replace(/<details\b[^>]*>[\s\S]*?<\/details>/gi, "");
}

function happeningMarkup(
  rankingState: "READY" | "INSUFFICIENT_EVIDENCE",
  limitations: readonly string[],
): string {
  return renderToStaticMarkup(
    createElement(HappeningBand, {
      happening: happeningView({
        status: "complete",
        busy: false,
        stalled: false,
        rankingState,
        limitations,
      }),
      busy: false,
      showRecovery: false,
      canResubmit: false,
      onResubmit: () => undefined,
    }),
  );
}

describe("UI-R first-read polish", () => {
  it("uses one G public stamp pair on happening and story", () => {
    const shownHappening = happeningMarkup("READY", []);
    const shownStory = renderToStaticMarkup(
      createElement(ResultStory, {
        view: presentResultStory({ snapshot: oracle0630Snapshot }),
      }),
    );
    expect(shownHappening).toContain(PUBLIC_STATUS.SPATIAL_ORDERING_SUPPORTED);
    expect(shownStory).toContain(STAMP_SUPPORTED);
    expect(STAMP_SUPPORTED).toBe(PUBLIC_STATUS.SPATIAL_ORDERING_SUPPORTED);
    expect(shownHappening).not.toContain("ORDER SHOWN");
    expect(shownStory).not.toContain("ORDER SHOWN");
    expect(shownStory).toContain(SUFFICIENT_HEADLINE);

    const withheldHappening = happeningMarkup("INSUFFICIENT_EVIDENCE", [
      THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT,
    ]);
    const withheldStory = renderToStaticMarkup(
      createElement(ResultStory, {
        view: presentResultStory({ snapshot: oracle0701Snapshot }),
      }),
    );
    expect(withheldHappening).toContain(PUBLIC_STATUS.SPATIAL_ORDERING_WITHHELD);
    expect(withheldStory).toContain(STAMP_WITHHELD);
    expect(STAMP_WITHHELD).toBe(PUBLIC_STATUS.SPATIAL_ORDERING_WITHHELD);
    expect(withheldHappening).not.toContain("ORDER WITHHELD");
    expect(withheldStory).not.toContain("ORDER WITHHELD");
    expect(withheldStory).toContain(INSUFFICIENT_HEADLINE);
    expect(INSUFFICIENT_HEADLINE.toLowerCase()).not.toContain("temperature");
    expect(INSUFFICIENT_HEADLINE).not.toMatch(/°C/);
    const withheldVisible = withheldHappening.replace(/<[^>]+>/g, " ");
    const withheldSr = withheldHappening.match(
      /data-testid="evidence-state"[^>]*>([^<]*)</,
    )?.[1];
    expect(withheldSr).toBe(PUBLIC_STATUS.SPATIAL_ORDERING_WITHHELD);
    expect(withheldVisible).not.toContain("INSUFFICIENT_EVIDENCE");
    expect(withheldVisible).not.toContain("INSUFFICIENT EVIDENCE");
  });

  it("does not paint catalog tokens or GEOID as the hero", () => {
    const chips = renderToStaticMarkup(
      createElement(ContextBar, { source: "REPLAY", clockDate: "2022-06-30" }),
    );
    expect(chips).toContain(CHIP_WINDOW_ID);
    expect(chips).toContain(CHIP_WINDOW);
    expect(chips).toContain("Phoenix demonstration area");
    expect(chips).toContain("25-zone analysis window");
    expect(chips).not.toContain("phoenix-demo");
    expect(chips).not.toMatch(/\bGEOID\b/);
  });

  it("keeps the capability spine out of operational first-read", () => {
    const html = renderToStaticMarkup(createElement(CapabilityExpansion));
    const visible = firstRead(html);
    expect(html).toContain('data-testid="capability-sequence"');
    expect(html).toContain("Research sequence — not live product modes");
    expect(visible).not.toContain("OBSERVE");
    expect(visible).not.toContain("ANTICIPATE");
    expect(visible).not.toMatch(/>ACT</);
    expect(visible).not.toContain("Current");
    expect(visible).not.toContain("Forecast");
    expect(visible).not.toContain("Scenario");
    expect(visible).not.toContain("Overnight");
    expect(html).not.toContain("TimelineBar");
    expect(html).not.toMatch(/<details[^>]*\sopen[\s>]/);
  });

  it("does not leak INTERVENTION PRIORITY, backend order, or 17-decimal S on first-read", () => {
    const shown = firstRead(
      renderToStaticMarkup(
        createElement(ResultStory, {
          view: presentResultStory({ snapshot: oracle0630Snapshot }),
        }),
      ),
    );
    const withheld = firstRead(
      renderToStaticMarkup(
        createElement(ResultStory, {
          view: presentResultStory({ snapshot: oracle0701Snapshot }),
        }),
      ),
    );
    const provenance = renderToStaticMarkup(
      createElement(ProvenanceBand, { snapshot: oracle0630Snapshot }),
    );
    const blob = [shown, withheld, provenance, happeningMarkup("READY", [])].join(
      "\n",
    );
    expect(blob).not.toContain("INTERVENTION PRIORITY");
    expect(blob).not.toMatch(/backend order/i);
    expect(shown).not.toContain(String(ORACLE_S_SUFFICIENT));
    expect(withheld).not.toContain(String(ORACLE_S_INSUFFICIENT));
    expect(provenance).toContain('data-testid="analysis-detail"');
    expect(provenance).not.toMatch(
      /data-testid="analysis-detail"[^>]*\sopen[\s>]/,
    );
  });

  it("keeps dual maps, TimelineBar, and fake horizons off the judge path", () => {
    const shell = readFileSync(path.join(here, "JudgeShell.tsx"), "utf8");
    const mapBand = readFileSync(path.join(here, "MapBand.tsx"), "utf8");
    expect(shell).not.toContain("TimelineBar");
    expect(shell).not.toContain("MapStage");
    expect(mapBand).not.toContain("MapStage");
    expect(mapBand).toContain("JudgeMap");
    expect(shell).not.toMatch(/["']Current["']/);
    expect(shell).not.toMatch(/["']Forecast["']/);
    expect(shell).not.toMatch(/["']Scenario["']/);
    expect(shell).not.toMatch(/["']Overnight["']/);
  });
});
