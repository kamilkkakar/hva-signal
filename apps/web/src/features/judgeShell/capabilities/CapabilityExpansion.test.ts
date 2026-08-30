import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { CapabilityExpansion } from "./CapabilityExpansion";
import {
  ACTION_MATURITY,
  AFTERHEAT_MATURITY,
  FORBIDDEN_CAPABILITY_PHRASES,
  HEATDOSE_MATURITY,
  HOSTED_LIVE_MATURITY,
  PLACE_SEARCH_MATURITY,
  PROBABILITY_MATURITY,
  SIGNAL_A_MATURITY,
  SIGNAL_B_MATURITY,
  WBGT_MATURITY,
} from "./copy";

function render() {
  return renderToStaticMarkup(createElement(CapabilityExpansion)).replaceAll(
    "&amp;",
    "&",
  );
}

describe("CapabilityExpansion", () => {
  it("renders a text-only ledger with frozen statuses", () => {
    const html = render();
    expect(html).toContain('data-testid="capability-expansion"');
    expect(html).toContain('data-fake-gauges="false"');
    expect(html).toContain('data-public-b="cached"');
    expect(html).toContain('data-search-geo="disabled"');
    expect(html).toContain('data-hosted-live="disabled"');
    expect(html).toContain("Beyond a snapshot");
    expect(html).toContain("Active capability expansion");
    expect(html).toContain(SIGNAL_A_MATURITY);
    expect(html).toContain(SIGNAL_B_MATURITY);
    expect(html).toContain(HEATDOSE_MATURITY);
    expect(html).toContain(AFTERHEAT_MATURITY);
    expect(html).toContain(WBGT_MATURITY);
    expect(html).toContain(PROBABILITY_MATURITY);
    expect(html).toContain(ACTION_MATURITY);
    expect(html).toContain(PLACE_SEARCH_MATURITY);
    expect(html).toContain(HOSTED_LIVE_MATURITY);
    expect(html).toContain("We do not score this yet");
    expect(html).toContain("Research sequence — not live product modes");
    expect(html).toMatch(
      /<details class="capability-sequence"[^>]*>[\s\S]*<ol class="capability-spine"/,
    );
    expect(html).not.toMatch(/<details[^>]*\sopen[\s>]/);
  });

  it("does not render gauges, meters, or numeric HeatDose/WBGT/probability values", () => {
    const html = render();
    expect(html).not.toContain("<progress");
    expect(html).not.toContain("<meter");
    expect(html).not.toContain('role="progressbar"');
    expect(html).not.toContain("aria-valuenow");
    expect(html).not.toContain("capability-gauge");
    expect(html).not.toMatch(/heatdose[^<]*\d/i);
    expect(html).not.toMatch(/wbgt[^<]*\d/i);
    expect(html).not.toMatch(/probability[^<]*\d/i);
    expect(html).not.toMatch(/\d+%/);
    expect(html).toContain('data-numeric-public="false"');
    expect(html).not.toContain('data-numeric-public="true"');
  });

  it("does not claim unpublished surfaces and omits the fake timeline", () => {
    const html = render();
    const b = html.match(
      /data-testid="capability-maturity-signal_b">[\s\S]*?<\/p>/,
    );
    expect(b?.[0]).toContain("AVAILABLE NOW — CACHED EVIDENCE");
    expect(b?.[0]).not.toContain("INTEGRATION TESTING");
    expect(html.toLowerCase()).not.toContain("01 current");
    expect(html).not.toContain("Forecast");
    expect(html).not.toContain("Scenario");
    const lower = html.toLowerCase();
    for (const phrase of FORBIDDEN_CAPABILITY_PHRASES) {
      expect(lower.includes(phrase)).toBe(false);
    }
  });
});
