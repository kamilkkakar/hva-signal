import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import {
  FORBIDDEN_AUTH_PHRASES,
  FORBIDDEN_L6_PHRASES,
  FORBIDDEN_LIVE_CHROME,
  FORBIDDEN_SPEND_PHRASES,
} from "./copy";
import { fixturePair } from "./fixtures";
import { SignalRail } from "./SignalRail";

const ENABLE = { selectedTimeSnapshotInterface: true } as const;

function render(scene: Parameters<typeof fixturePair>[0], flags = ENABLE) {
  const pair = fixturePair(scene);
  return renderToStaticMarkup(
    createElement(SignalRail, {
      historical: pair.historical,
      selectedTime: pair.selectedTime,
      flags,
    }),
  );
}

describe("SignalRail gate", () => {
  it("renders nothing when the selected-time interface is off", () => {
    expect(render("a_not_prepared_b_cached", {})).toBe("");
  });
});

describe("independent A/B sections", () => {
  it("renders both sections when A is NOT_PREPARED and B is cached", () => {
    const html = render("a_not_prepared_b_cached");
    expect(html).toContain('data-testid="signal-a"');
    expect(html).toContain('data-testid="signal-b"');
    expect(html).toContain("REFERENCE NOT PREPARED");
    expect(html).toContain("CACHED");
    expect(html).toContain("reuse-only");
    expect(html).toContain("combined score is not authorized");
    expect(html).toContain('data-combined-score-authorized="false"');
    expect(html).toContain('data-overall-complete="false"');
    expect(html).not.toContain("combined_score");
    expect(html).not.toContain("data-testid=\"live-demo-confirmation\"");
  });

  it("keeps B visible when A is insufficient", () => {
    const html = render("a_insufficient_b_ready");
    expect(html).toContain('data-a-state="historical_insufficient"');
    expect(html).toContain('data-b-state="b_ready"');
    expect(html).toContain("Selected-Time Thermal Snapshot");
    expect(html).toContain("°C");
  });

  it("renders unavailable, fetching, partial, and ready without live chrome", () => {
    expect(render("a_not_prepared_b_unavailable")).toContain("UNAVAILABLE");
    expect(render("a_not_prepared_b_unavailable")).toContain("not treated as cool");
    expect(render("a_not_prepared_b_fetching")).toContain("FETCHING");
    const partial = render("a_not_prepared_b_partial");
    expect(partial).toContain("PARTIAL");
    expect(partial).toContain("unknown");
    expect(partial).toContain("FIX-1714000-01");
    const ready = render("a_not_prepared_b_ready");
    expect(ready).toContain(">READY<");
    expect(ready).toContain("absolute °C");
    expect(ready).toContain("not live");
    expect(ready).not.toContain("FORTYGUARD LIVE");
  });

  it("hides future live-demo confirmation by default", () => {
    const html = render("a_not_prepared_live_demo");
    expect(html).not.toContain("data-testid=\"live-demo-confirmation\"");
    expect(html).toContain("UNAVAILABLE");
    const shown = render("a_not_prepared_live_demo", {
      selectedTimeSnapshotInterface: true,
      liveDemoConfirmation: true,
    });
    expect(shown).toContain("data-testid=\"live-demo-confirmation\"");
    expect(shown).toContain("Generate a live thermal snapshot?");
  });
});

describe("L6 and chrome bans", () => {
  it("does not let NOT_PREPARED copy look like low risk", () => {
    const html = render("a_not_prepared_b_cached").toLowerCase();
    expect(html).toContain("not treated as safe");
    expect(html).toContain("reference not prepared");
    expect(html).toContain('data-a-tone="not-prepared"');
    for (const phrase of FORBIDDEN_L6_PHRASES) {
      expect(html.includes(phrase)).toBe(false);
    }
    expect(html).not.toContain("preparedness priority");
  });

  it("omits login, spend, and live tape chrome", () => {
    const html = [
      render("a_not_prepared_b_cached"),
      render("a_not_prepared_b_unavailable"),
      render("a_not_prepared_b_ready"),
    ]
      .join("\n")
      .toLowerCase();
    for (const phrase of FORBIDDEN_AUTH_PHRASES) {
      expect(html.includes(phrase)).toBe(false);
    }
    for (const phrase of FORBIDDEN_SPEND_PHRASES) {
      expect(html.includes(phrase)).toBe(false);
    }
    for (const phrase of FORBIDDEN_LIVE_CHROME) {
      expect(html.includes(phrase)).toBe(false);
    }
    expect(html).toContain("does not require an account");
  });
});
