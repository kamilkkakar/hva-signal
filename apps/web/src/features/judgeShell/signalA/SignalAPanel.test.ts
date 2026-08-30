import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import {
  FORBIDDEN_CHROME_METHOD,
  FORBIDDEN_JUDGE_PHRASES,
  chromeUsesForbiddenPhrase,
  STAMP_HISTORY_NOT_PREPARED,
  STAMP_ORDER_SHOWN,
  STAMP_ORDER_WITHHELD,
} from "./copy";
import { clusteredResult } from "../charts/fixtures";
import { presentSignalA } from "./presentation";
import { SignalAPanel } from "./SignalAPanel";

function render(props: Parameters<typeof SignalAPanel>[0]): string {
  return renderToStaticMarkup(createElement(SignalAPanel, props));
}

function chromeOf(html: string): string {
  const start = html.indexOf('data-testid="siga-chrome"');
  const method = html.indexOf('data-testid="siga-method"');
  return html.slice(start, method === -1 ? undefined : method);
}

describe("SignalAPanel", () => {
  it("renders ORDER SHOWN chrome and keeps Method nouns in the drawer", () => {
    const html = render({
      view: presentSignalA({
        kind: "order_shown",
        zoneId: "04013107800",
        order: 1,
      }),
      zoneId: "04013107800",
      order: 1,
    });
    expect(html).toContain('data-testid="judge-signal-a"');
    expect(html).toContain(STAMP_ORDER_SHOWN);
    expect(html).toContain("data-fills=\"25\"");
    expect(html).toContain("data-blocks-b=\"false\"");
    expect(html).toContain("q_A");
    expect(html).toContain("Decision 8");
    expect(html).toContain(">S is the normalized spread");
    const chrome = chromeOf(html);
    expect(chrome).toContain(STAMP_ORDER_SHOWN);
    for (const token of FORBIDDEN_CHROME_METHOD) {
      expect(chrome.includes(token), token).toBe(false);
    }
  });

  it("renders ORDER WITHHELD as the product with zero fills", () => {
    const html = render({ input: { kind: "order_withheld" } });
    expect(html).toContain(STAMP_ORDER_WITHHELD);
    expect(html).not.toContain("INSUFFICIENT EVIDENCE");
    expect(html).toContain("data-insufficient-is-feature=\"true\"");
    expect(html).toContain("data-fills=\"0\"");
    expect(html).toContain("data-hover=\"off\"");
    expect(html).toContain("flat night");
    expect(html).not.toContain('data-testid="siga-hover"');
  });

  it("keeps HISTORY NOT PREPARED on a different stamp", () => {
    const html = render({ input: { historyPrepared: false } });
    expect(html).toContain(STAMP_HISTORY_NOT_PREPARED);
    expect(html).not.toContain(`>${STAMP_ORDER_WITHHELD}<`);
    expect(html).toContain("Geography ready is not history ready");
  });

  it("puts the historical-position strip in chrome without leaking q_A", () => {
    const html = render({
      input: { kind: "order_withheld" },
      result: clusteredResult(),
    });
    expect(html).toContain('data-testid="historical-position-strip"');
    expect(html).toContain("ORDERING WITHHELD");
    const chrome = chromeOf(html);
    expect(chrome).toContain("LOWER POSITION IN OWN HISTORY");
    for (const token of FORBIDDEN_CHROME_METHOD) {
      expect(chrome.includes(token), token).toBe(false);
    }
  });

  it("omits forbidden judge phrases from chrome", () => {
    const html = [
      render({ input: { kind: "order_shown" } }),
      render({ input: { kind: "order_withheld" } }),
      render({ input: { historyPrepared: false } }),
    ]
      .map(chromeOf)
      .join("\n");
    for (const phrase of FORBIDDEN_JUDGE_PHRASES) {
      expect(chromeUsesForbiddenPhrase(html, phrase), phrase).toBe(false);
    }
  });
});
