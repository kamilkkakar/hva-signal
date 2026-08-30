import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import {
  REPLAY_0701_GEOMETRY,
  REPLAY_0701_POLICY,
  REPLAY_0701_RESULT,
  replay0701Snapshot,
} from "./fixtures";
import { ResultSurface } from "./ResultSurface";

const here = path.dirname(fileURLToPath(import.meta.url));
const css = readFileSync(path.join(here, "results.css"), "utf8");

describe("result card overflow contracts", () => {
  it("zeros grid min-content so the third column cannot blow the page", () => {
    expect(css).toContain(
      "grid-template-columns: minmax(0, 16.25rem) minmax(0, 1fr) minmax(0, 18.75rem);",
    );
    expect(css).toMatch(/\.result-overflow-grid\s*>\s*\*\s*\{[^}]*min-width:\s*0/);
    expect(css).toContain("overflow-wrap: anywhere");
    expect(css).toContain("word-break: break-word");
    expect(css).toMatch(/\.result-column\s*\{[^}]*overflow-x:\s*hidden/s);
    expect(css).toMatch(/\.result-column\s*\{[^}]*overflow-y:\s*auto/s);
    expect(css).not.toMatch(/overflow-x:\s*auto\s*;/);
    expect(css).toContain("grid-column: 1 / -1");
    expect(css).toContain("text-overflow: ellipsis");
  });

  it("after 07-01 replay, long tokens live in the accordion not the 300px column", () => {
    const html = renderToStaticMarkup(
      createElement(ResultSurface, {
        snapshot: replay0701Snapshot,
        rankingState: "INSUFFICIENT_EVIDENCE",
      }),
    );
    expect(html).toContain('data-testid="result-overflow-page"');
    expect(html).toContain('data-testid="result-column"');
    expect(html).toContain('data-testid="analysis-detail"');
    expect(html).toContain("ORDER WITHHELD");

    const columnStart = html.indexOf('data-testid="result-column"');
    const accordionStart = html.indexOf('data-testid="analysis-detail"');
    expect(columnStart).toBeGreaterThan(-1);
    expect(accordionStart).toBeGreaterThan(columnStart);
    const columnHtml = html.slice(columnStart, accordionStart);
    expect(columnHtml).not.toContain(REPLAY_0701_GEOMETRY);
    expect(columnHtml).not.toContain(REPLAY_0701_POLICY);
    expect(columnHtml).not.toContain(REPLAY_0701_RESULT);
    expect(columnHtml).not.toContain('data-testid="decision8-evidence-panel"');

    const accordionHtml = html.slice(accordionStart);
    expect(accordionHtml).toContain(REPLAY_0701_GEOMETRY);
    expect(accordionHtml).toContain(REPLAY_0701_POLICY);
    expect(accordionHtml).toContain(REPLAY_0701_RESULT);
    expect(accordionHtml).toContain('data-testid="decision8-geometry-token-copy"');
  });
});
