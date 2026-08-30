import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { composeSelectedAreaStory } from "./compose";
import { R2_TEXT } from "./copy";
import { AREA_1, contextView, documentFor, sufficientResult } from "./fixtures";
import { SelectedAreaStoryPanel } from "./SelectedAreaStoryPanel";

function firstRead(html: string): string {
  return html.replace(/<details\b[^>]*>[\s\S]*?<\/details>/gi, "");
}

describe("selected area story public chrome", () => {
  it("uses historical-position language and keeps q_A / Decision 8 in closed details", () => {
    const story = composeSelectedAreaStory({
      selectedGeoid: AREA_1,
      result: sufficientResult(),
      context: contextView(),
      document: documentFor(contextView()),
    });
    const html = renderToStaticMarkup(createElement(SelectedAreaStoryPanel, { story, mode: "THERMAL" }));
    const visible = firstRead(html);
    expect(visible).toContain("historical position");
    expect(visible).toContain("thermal order is shown");
    expect(visible).not.toContain("q_A");
    expect(visible).not.toContain("Decision 8");
    expect(visible).not.toContain("SUFFICIENT");
    expect(html).toContain("q_A 0.812");
    expect(html).toContain("Decision 8 SUFFICIENT");
    expect(html).not.toMatch(/<details[^>]*\sopen[\s>]/);
  });

  it("drops q_A from the R2 review sentence", () => {
    expect(R2_TEXT).toContain("thermal order");
    expect(R2_TEXT).not.toContain("q_A");
    expect(R2_TEXT).toContain("not an intervention priority");
  });
});
