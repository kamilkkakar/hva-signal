import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import {
  FORBIDDEN_STORY_CHROME,
  INSUFFICIENT_HEADLINE,
  INSUFFICIENT_SUPPORTS,
  SUFFICIENT_HEADLINE,
  SUFFICIENT_SUPPORTS,
} from "./copy";
import {
  ORACLE_GEOMETRY,
  ORACLE_POLICY,
  ORACLE_S_INSUFFICIENT,
  ORACLE_S_INSUFFICIENT_PUBLIC,
  ORACLE_S_SUFFICIENT,
  ORACLE_S_SUFFICIENT_PUBLIC,
  oracle0630Snapshot,
  oracle0701Snapshot,
} from "./fixtures";
import { presentResultStory } from "./presentation";
import { ResultStory } from "./ResultStory";

function renderStory(snapshot: Parameters<typeof presentResultStory>[0]["snapshot"]) {
  const view = presentResultStory({ snapshot });
  return renderToStaticMarkup(createElement(ResultStory, { view }));
}

describe("ResultStory chrome", () => {
  it("tells the 2022-06-30 sufficient story without debug tokens", () => {
    const html = renderStory(oracle0630Snapshot);
    expect(html).toContain('data-story-kind="sufficient"');
    expect(html).toContain(SUFFICIENT_HEADLINE);
    expect(html).toContain(SUFFICIENT_SUPPORTS);
    expect(html).toContain("25 zones");
    expect(html).toContain("03:00 local");
    expect(html).toContain("Historical comparison 2022–2024");
    expect(html).toContain(ORACLE_S_SUFFICIENT_PUBLIC);
    expect(html).toContain("0.10");
    expect(html).not.toContain(String(ORACLE_S_SUFFICIENT));
    expect(html).not.toContain(ORACLE_POLICY);
    expect(html).not.toContain(ORACLE_GEOMETRY);
    expect(html).not.toContain("FULL_REFERENCE");
    expect(html).not.toContain("GRAPH-POPULATED");
    expect(html).not.toContain("INTERVENTION PRIORITY");
  });

  it("tells the 2022-07-01 unranked story without calling it a failed job", () => {
    const html = renderStory(oracle0701Snapshot);
    expect(html).toContain('data-story-kind="insufficient"');
    expect(html).toContain(INSUFFICIENT_HEADLINE);
    expect(html).toContain(INSUFFICIENT_SUPPORTS);
    expect(html).toContain("Zones stay unranked");
    expect(html).toContain("Do not use thermal ranking alone");
    expect(html).toContain(ORACLE_S_INSUFFICIENT_PUBLIC);
    expect(html).not.toContain(String(ORACLE_S_INSUFFICIENT));
    expect(html.toLowerCase()).not.toMatch(/error|blocked job|failure/);
    expect(html).not.toContain(ORACLE_POLICY);
    expect(html).not.toContain(ORACLE_GEOMETRY);
  });

  it("keeps both oracle faces free of forbidden primary chrome", () => {
    const html = [renderStory(oracle0630Snapshot), renderStory(oracle0701Snapshot)]
      .join("\n")
      .toLowerCase();
    for (const token of FORBIDDEN_STORY_CHROME) {
      expect(html).not.toContain(token.toLowerCase());
    }
  });
});
