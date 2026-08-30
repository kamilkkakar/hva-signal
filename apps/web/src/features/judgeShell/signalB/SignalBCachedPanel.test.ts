import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { SIGNAL_B_LAYER_TITLE, SIGNAL_B_MEANING_COPY } from "@/features/analysisMap/signalBPolicy";
import { SignalBCachedPanel } from "./SignalBCachedPanel";
import { CACHED_B_WORDING, presentPublicCachedB } from "./cachedPhoenix";

const here = path.dirname(fileURLToPath(import.meta.url));

function firstRead(html: string): string {
  return html.replace(/<details\b[^>]*>[\s\S]*?<\/details>/gi, "");
}

describe("public Signal B cached panel first-read", () => {
  it("leads with rounded facts and keeps q_A / Decision 8 in a footnote", () => {
    const html = renderToStaticMarkup(
      createElement(SignalBCachedPanel, { selectedZoneId: "04013106400" }),
    );
    const visible = firstRead(html);
    const facts = presentPublicCachedB("04013106400");
    expect(html).toContain(CACHED_B_WORDING);
    expect(html).toContain('data-coverage="25/25"');
    expect(html).toContain('data-source="fortyguard_cached"');
    expect(html).toContain('data-rank="no"');
    expect(visible).toContain("25/25");
    expect(visible).toContain("CACHED");
    expect(visible).toContain(facts.rangeLabel);
    expect(visible).toContain(facts.selectedLabel ?? "");
    expect(visible).not.toContain("q_A");
    expect(visible).not.toContain("Decision 8");
    expect(visible).not.toContain("INTERVENTION PRIORITY");
    expect(visible).not.toMatch(/priority map|backend_order/i);
    expect(html).not.toContain('data-testid="signal-b-zones"');
    expect(html).not.toContain('data-testid="signal-b-zone-table"');
    expect((visible.match(/04013\d{6}/g) ?? []).length).toBeLessThanOrEqual(1);
    expect(visible).not.toMatch(/\d+\.\d{4,}/);
    expect(html).toContain("not q_A / not Decision 8");
    expect(html).toContain('data-testid="signal-b-footnote"');
    expect(html).not.toMatch(/<details[^>]*\sopen[\s>]/);
  });

  it("does not mount the 25-zone dump or SignalBSection", () => {
    const source = readFileSync(path.join(here, "SignalBCachedPanel.tsx"), "utf8");
    expect(source).not.toContain("SignalBSection");
    expect(source).not.toContain("TEST_ONLY");
    expect(source).not.toContain("decision_ui_2");
    expect(source).toContain("showZoneTable={false}");
    expect(SIGNAL_B_MEANING_COPY).not.toMatch(/q_A|Decision 8|rank|priority/i);
    expect(SIGNAL_B_LAYER_TITLE).toBe("Selected-Time Thermal Snapshot");
  });
});
