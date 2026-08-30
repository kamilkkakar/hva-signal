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

const D1B_REFERENCE =
  "PHX_ZTSI_REF_V1__US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f__ANCHOR_2025-07-15__S2_PM15_CALENDAR_DAYS__YEARS_2022_2023_2024__HOUR_0300_LOCAL__GRANULARITY_100M";

describe("result card overflow contracts", () => {
  it("uses a single minmax(0, 1fr) stack so no rail can blow the page", () => {
    expect(css).toContain("grid-template-columns: minmax(0, 1fr)");
    expect(css).not.toContain(
      "minmax(0, 16.25rem) minmax(0, 1fr) minmax(0, 18.75rem)",
    );
    expect(css).not.toMatch(/260px\s+1fr\s+300px/);
    expect(css).toMatch(/\.result-map-primary\s*>\s*\*\s*\{[^}]*min-width:\s*0/);
    expect(css).toContain("overflow-wrap: anywhere");
    expect(css).toContain("word-break: break-word");
    expect(css).not.toMatch(/overflow-x:\s*auto\s*;/);
    expect(css).toContain("text-overflow: ellipsis");
    expect(css).toMatch(/\.result-d8-panel\s*\{[^}]*grid-column:\s*1\s*\/\s*-1/s);
  });

  it("after 07-01 replay, long tokens live in the accordion not the result band", () => {
    const html = renderToStaticMarkup(
      createElement(ResultSurface, {
        snapshot: replay0701Snapshot,
        rankingState: "INSUFFICIENT_EVIDENCE",
      }),
    );
    expect(html).toContain('data-testid="result-overflow-page"');
    expect(html).toContain('data-testid="result-map-slot"');
    expect(html).toContain('data-testid="result-column"');
    expect(html).toContain('data-testid="analysis-detail"');
    expect(html).toContain("ORDER WITHHELD");
    expect(html).not.toContain("result-overflow-grid");

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

  it("keeps the 188-character D1B reference in the static overflow fixture, not a rail", () => {
    const fixture = readFileSync(path.join(here, "fixtures/replay-0701.html"), "utf8");
    expect(D1B_REFERENCE.length).toBeGreaterThan(180);
    expect(fixture).toContain(D1B_REFERENCE);
    expect(fixture).toContain("result-map-primary");
    expect(fixture).not.toContain("result-overflow-grid");
    const columnStart = fixture.indexOf('data-testid="result-column"');
    const accordionStart = fixture.indexOf('data-testid="analysis-detail"');
    expect(fixture.slice(columnStart, accordionStart)).not.toContain(D1B_REFERENCE);
    expect(fixture.slice(accordionStart)).toContain(D1B_REFERENCE);
  });
});
