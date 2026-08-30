import { readFileSync } from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";

const VIEWPORTS = [
  { width: 1920, height: 1080 },
  { width: 1440, height: 900 },
  { width: 1366, height: 768 },
  { width: 1280, height: 800 },
  { width: 1024, height: 768 },
] as const;

const resultsDir = path.join(
  process.cwd(),
  "apps/web/src/features/judgeShell/results",
);

const GEOMETRY =
  "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f";
const D1B_REFERENCE =
  "PHX_ZTSI_REF_V1__US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f__ANCHOR_2025-07-15__S2_PM15_CALENDAR_DAYS__YEARS_2022_2023_2024__HOUR_0300_LOCAL__GRANULARITY_100M";

function harnessDocument(): string {
  const css = readFileSync(path.join(resultsDir, "results.css"), "utf8");
  const body = readFileSync(
    path.join(resultsDir, "fixtures/replay-0701.html"),
    "utf8",
  );
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
html, body { margin: 0; width: 100%; min-height: 100%; }
${css}
</style></head><body>${body}</body></html>`;
}

async function overflowBox(page: Page) {
  return page.evaluate(() => {
    const root = document.documentElement;
    const surface = document.querySelector("[data-testid='result-overflow-page']");
    const column = document.querySelector("[data-testid='result-column']");
    const accordion = document.querySelector("[data-testid='analysis-detail']");
    const panel = document.querySelector("[data-testid='decision8-evidence-panel']");
    return {
      rootScroll: root.scrollWidth,
      rootClient: root.clientWidth,
      bodyScroll: document.body.scrollWidth,
      bodyClient: document.body.clientWidth,
      pageScroll: surface instanceof HTMLElement ? surface.scrollWidth : 0,
      pageClient: surface instanceof HTMLElement ? surface.clientWidth : 0,
      columnScroll: column instanceof HTMLElement ? column.scrollWidth : 0,
      columnClient: column instanceof HTMLElement ? column.clientWidth : 0,
      accordionScroll: accordion instanceof HTMLElement ? accordion.scrollWidth : 0,
      accordionClient: accordion instanceof HTMLElement ? accordion.clientWidth : 0,
      panelScroll: panel instanceof HTMLElement ? panel.scrollWidth : 0,
      panelClient: panel instanceof HTMLElement ? panel.clientWidth : 0,
    };
  });
}

function expectNoHorizontalScroll(
  box: Awaited<ReturnType<typeof overflowBox>>,
  label: string,
) {
  expect(box.rootScroll, `${label} documentElement`).toBeLessThanOrEqual(
    box.rootClient + 1,
  );
  expect(box.bodyScroll, `${label} body`).toBeLessThanOrEqual(box.bodyClient + 1);
  expect(box.pageScroll, `${label} result page`).toBeLessThanOrEqual(
    box.pageClient + 1,
  );
  expect(box.columnScroll, `${label} result band`).toBeLessThanOrEqual(
    box.columnClient + 1,
  );
  expect(box.accordionScroll, `${label} D8 accordion`).toBeLessThanOrEqual(
    box.accordionClient + 1,
  );
  expect(box.panelScroll, `${label} D8 panel`).toBeLessThanOrEqual(
    box.panelClient + 1,
  );
}

test.describe("result cards 07-01 overflow", () => {
  test("map-primary stack has no page or panel horizontal scroll after 07-01 tokens", async ({
    page,
  }) => {
    const html = harnessDocument();
    for (const viewport of VIEWPORTS) {
      await page.setViewportSize(viewport);
      await page.setContent(html, { waitUntil: "domcontentloaded" });
      await expect(page.getByTestId("result-column")).toBeVisible();
      await expect(page.getByTestId("result-map-slot")).toBeVisible();
      await expect(page.getByTestId("analysis-detail")).toHaveAttribute("open", "");
      await expect(page.getByTestId("decision8-zone-geometry")).toContainText(
        GEOMETRY,
      );
      await expect(page.getByTestId("decision8-reference-version")).toContainText(
        D1B_REFERENCE,
      );
      await expect(page.getByTestId("signal-a-stamp")).toHaveText("ORDER WITHHELD");
      const column = page.getByTestId("result-column");
      await expect(column).not.toContainText("US_CENSUS_TIGERLINE");
      await expect(column).not.toContainText("PHX_NORMALIZED_HAZARD");
      await expect(column).not.toContainText("PHX_ZTSI_REF_V1__");
      expectNoHorizontalScroll(
        await overflowBox(page),
        `${viewport.width}x${viewport.height} 07-01`,
      );
    }
  });
});
