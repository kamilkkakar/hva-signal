import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Decision8AccordionView } from "./Decision8Accordion";
import {
  REPLAY_0701_GEOMETRY,
  REPLAY_0701_JOB_ID,
  REPLAY_0701_POLICY,
  REPLAY_0701_RESULT,
  replay0701Snapshot,
} from "./fixtures";
import { resultCardsFromSnapshot } from "./presentation";
import { ResultCard } from "./ResultCard";
import { ResultColumn } from "./ResultColumn";

describe("ResultCard 07-01 face", () => {
  it("renders one question, one message, and few values without long D8 tokens", () => {
    const view = resultCardsFromSnapshot({
      snapshot: replay0701Snapshot,
      rankingState: "INSUFFICIENT_EVIDENCE",
    });
    const html = renderToStaticMarkup(createElement(ResultCard, { card: view.a }));
    expect(html).toContain('data-testid="result-card-a-question"');
    expect(html).toContain('data-testid="result-card-a-message"');
    expect(html).toContain('data-testid="result-card-a-values"');
    expect(html).toContain("ORDER WITHHELD");
    expect(html).not.toContain(REPLAY_0701_GEOMETRY);
    expect(html).not.toContain(REPLAY_0701_POLICY);
    expect(html).not.toContain(REPLAY_0701_RESULT);
    expect(html).not.toContain(REPLAY_0701_JOB_ID);
    expect(html).not.toContain("INSUFFICIENT_EVIDENCE");
    expect(html).not.toMatch(/fortyguard/i);
  });
});

describe("ResultColumn 07-01", () => {
  it("keeps the result band short — Decision 8 stays out of the cards", () => {
    const view = resultCardsFromSnapshot({
      snapshot: replay0701Snapshot,
      rankingState: "INSUFFICIENT_EVIDENCE",
    });
    const html = renderToStaticMarkup(createElement(ResultColumn, { view }));
    expect(html).toContain('data-testid="result-column"');
    expect(html).toContain('aria-label="Decision panel"');
    expect(html).toContain("ORDER WITHHELD");
    expect(html).toContain("AVAILABLE NOW — CACHED EVIDENCE");
    expect(html).not.toContain('data-testid="decision8-evidence-panel"');
    expect(html).not.toContain(REPLAY_0701_GEOMETRY);
    expect(html).not.toContain(REPLAY_0701_POLICY);
  });
});

describe("Decision8Accordion 07-01", () => {
  it("keeps long Decision 8 analysis closed with copyable tokens inside", () => {
    const html = renderToStaticMarkup(
      createElement(Decision8AccordionView, { snapshot: replay0701Snapshot }),
    );
    expect(html).toContain('data-testid="analysis-detail"');
    expect(html).not.toMatch(/<details[^>]*\sopen/);
    expect(html).toContain('data-testid="decision8-evidence-panel"');
    expect(html).toContain(REPLAY_0701_POLICY);
    expect(html).toContain(REPLAY_0701_GEOMETRY);
    expect(html).toContain(REPLAY_0701_RESULT);
    expect(html).toContain(REPLAY_0701_JOB_ID);
    expect(html).toContain('data-testid="decision8-policy-token-copy"');
    expect(html).toContain('data-testid="decision8-geometry-token-copy"');
    expect(html).toContain('data-testid="job-id-copy"');
    expect(html).toContain(`data-full-value="${REPLAY_0701_POLICY}"`);
    expect(html).not.toMatch(/fortyguard/i);
  });

  it("stays closed when no result has arrived", () => {
    const html = renderToStaticMarkup(
      createElement(Decision8AccordionView, { snapshot: null }),
    );
    expect(html).toContain('data-testid="analysis-detail"');
    expect(html).not.toMatch(/<details[^>]*\sopen/);
  });
});
