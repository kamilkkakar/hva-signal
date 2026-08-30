import { readFileSync } from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";

const VIEWPORTS = [1920, 1440, 1280, 1024] as const;
const resultsDir = path.join(
  process.cwd(),
  "apps/web/src/features/judgeShell/results",
);

const GEOMETRY =
  "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f";

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
    return {
      rootScroll: root.scrollWidth,
      rootClient: root.clientWidth,
      bodyScroll: document.body.scrollWidth,
      bodyClient: document.body.clientWidth,
      pageScroll: surface instanceof HTMLElement ? surface.scrollWidth : 0,
      pageClient: surface instanceof HTMLElement ? surface.clientWidth : 0,
      columnScroll: column instanceof HTMLElement ? column.scrollWidth : 0,
      columnClient: column instanceof HTMLElement ? column.clientWidth : 0,
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
  expect(box.columnScroll, `${label} third column`).toBeLessThanOrEqual(
    box.columnClient + 1,
  );
}

test.describe("result cards 07-01 overflow", () => {
  test("third column and page have no horizontal scroll after 07-01 replay tokens", async ({
    page,
  }) => {
    const html = harnessDocument();
    for (const width of VIEWPORTS) {
      await page.setViewportSize({ width, height: 900 });
      await page.setContent(html, { waitUntil: "domcontentloaded" });
      await expect(page.getByTestId("result-column")).toBeVisible();
      await expect(page.getByTestId("analysis-detail")).toHaveAttribute("open", "");
      await expect(page.getByTestId("decision8-zone-geometry")).toContainText(
        GEOMETRY,
      );
      await expect(page.getByTestId("signal-a-stamp")).toHaveText("ORDER WITHHELD");
      const column = page.getByTestId("result-column");
      await expect(column).not.toContainText("US_CENSUS_TIGERLINE");
      await expect(column).not.toContainText("PHX_NORMALIZED_HAZARD");
      expectNoHorizontalScroll(await overflowBox(page), `${width} 07-01`);
    }
  });
});
