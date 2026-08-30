import { readFileSync } from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";

const VIEWPORTS = [
  { width: 1366, height: 768 },
  { width: 1280, height: 800 },
  { width: 1024, height: 768 },
] as const;

const shellDir = path.join(process.cwd(), "apps/web/src/features/judgeShell");

function harnessDocument(): string {
  const shellCss = readFileSync(path.join(shellDir, "judgeShell.css"), "utf8");
  const storyCss = readFileSync(
    path.join(shellDir, "resultStory/resultStory.css"),
    "utf8",
  );
  const body = readFileSync(
    path.join(shellDir, "fixtures/laptop-first-read.html"),
    "utf8",
  );
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
:root {
  --ops-wall: #232820;
  --plotter: #c2c8b4;
  --panel: #d3d8c6;
  --carbon: #10140e;
  --filament: #d56a1c;
  --stamp: #8f2d1c;
  --rule: #4e5748;
  --tape: #161a14;
  --muted: #4e5849;
  --font-display: "Barlow Condensed", "Arial Narrow", sans-serif;
  --font-body: "IBM Plex Sans", "Segoe UI", sans-serif;
  --font-mono: "IBM Plex Mono", ui-monospace, monospace;
}
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; width: 100%; font-family: var(--font-body); }
h1 { margin: 0.15rem 0 0; font-family: var(--font-display); letter-spacing: 0.06em; }
.eyebrow, .kicker {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 0.68rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}
.judge-map-canvas-stub {
  min-height: 100%;
  height: 100%;
  background: var(--plotter);
  display: grid;
  place-items: center;
}
${shellCss}
${storyCss}
</style></head><body>${body}</body></html>`;
}

async function firstReadBox(page: Page) {
  return page.evaluate(() => {
    const map = document.querySelector("[data-testid='judge-map']");
    const root = document.documentElement;
    if (!(map instanceof HTMLElement)) {
      return null;
    }
    const r = map.getBoundingClientRect();
    const visible = Math.min(r.bottom, window.innerHeight) - Math.max(r.top, 0);
    return {
      mapTop: r.top,
      mapBottom: r.bottom,
      mapHeight: r.height,
      visibleHeight: visible,
      viewportH: window.innerHeight,
      viewportW: window.innerWidth,
      pageOverflowX: root.scrollWidth > root.clientWidth + 1,
    };
  });
}

test.describe("laptop first-read map visibility", () => {
  test("map is in the first viewport at 1366, 1280, and 1024", async ({
    page,
  }) => {
    const html = harnessDocument();
    for (const viewport of VIEWPORTS) {
      await page.setViewportSize(viewport);
      await page.setContent(html, { waitUntil: "domcontentloaded" });
      await expect(page.getByTestId("judge-map")).toBeVisible();
      const box = await firstReadBox(page);
      expect(box, `${viewport.width}x${viewport.height} map box`).not.toBeNull();
      expect(box?.pageOverflowX, `${viewport.width} page overflow-x`).toBe(
        false,
      );
      expect(box?.mapTop, `${viewport.width} map top`).toBeLessThan(
        viewport.height - 120,
      );
      expect(
        box?.visibleHeight,
        `${viewport.width} visible map height`,
      ).toBeGreaterThan(180);
    }
  });
});
