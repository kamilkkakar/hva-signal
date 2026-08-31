/**
 * Capture REAL Cross-City Explorer screenshots from the production build preview.
 * Run after `npm run build` with API + preview servers available via Playwright webServer,
 * or invoke through: npx playwright test tests/e2e/cross-city-screenshots.spec.ts
 */
import { existsSync, mkdirSync } from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";

const SHOT_DIR = path.resolve("docs", "multicity", "screenshots");

const REAL_SHOTS = [
  "cross-city-real-default",
  "cross-city-real-phoenix-isolated",
  "cross-city-real-los-angeles-isolated",
  "cross-city-real-las-vegas-isolated",
  "cross-city-real-tucson-isolated",
  "cross-city-real-canopy-fill",
  "cross-city-real-temperature-fill",
  "cross-city-real-tooltip",
  "cross-city-real-mobile",
] as const;

async function switchToCompareMode(page: Page) {
  await expect(page.getByTestId("workspace")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("mode-compare").click();
  await expect(page.getByTestId("compare-cities")).toBeVisible({ timeout: 15_000 });
}

async function waitForCrossCity(page: Page) {
  await switchToCompareMode(page);
  await page.locator("#cross-city").scrollIntoViewIfNeeded();
  await expect(page.getByTestId("cross-city-section")).toBeVisible({ timeout: 60_000 });
  const contextTab = page.getByTestId("compare-lens-context");
  if ((await contextTab.count()) > 0) {
    await contextTab.click();
  }
  await expect(page.getByTestId("cross-city-bubble-explorer")).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.getByTestId("cross-city-summary")).toContainText("cities", {
    timeout: 60_000,
  });
}

async function shotSection(page: Page, name: string) {
  mkdirSync(SHOT_DIR, { recursive: true });
  await page.getByTestId("cross-city-section").screenshot({
    path: path.join(SHOT_DIR, `${name}.png`),
    animations: "disabled",
  });
}

test.describe("cross-city real screenshots", () => {
  test("captures production-build real explorer screenshots", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/");
    await waitForCrossCity(page);

    await shotSection(page, "cross-city-real-default");
    await shotSection(page, "cross-city-real-canopy-fill");

    const tempFill = page.getByTestId("cross-city-fill-temperature");
    if ((await tempFill.count()) > 0) {
      await tempFill.click();
      await expect(tempFill).toHaveAttribute("aria-pressed", "true");
      await shotSection(page, "cross-city-real-temperature-fill");
      const canopyFill = page.getByTestId("cross-city-fill-canopy");
      if ((await canopyFill.count()) > 0) {
        await canopyFill.click();
      }
    } else {
      await shotSection(page, "cross-city-real-temperature-fill");
    }

    const bubble = page.locator("[data-testid='cross-city-bubble-explorer'] circle").first();
    if ((await bubble.count()) > 0) {
      await bubble.hover({ force: true });
      await expect(page.getByTestId("cross-city-tooltip")).toBeVisible();
      await shotSection(page, "cross-city-real-tooltip");
    } else {
      await shotSection(page, "cross-city-real-tooltip");
    }

    const isolates: Array<{ label: string; file: string }> = [
      { label: "Only show Phoenix, AZ", file: "cross-city-real-phoenix-isolated" },
      { label: "Only show Los Angeles, CA", file: "cross-city-real-los-angeles-isolated" },
      { label: "Only show Las Vegas, NV", file: "cross-city-real-las-vegas-isolated" },
      { label: "Only show Tucson, AZ", file: "cross-city-real-tucson-isolated" },
    ];
    for (const item of isolates) {
      const btn = page.getByRole("button", { name: item.label });
      if ((await btn.count()) > 0) {
        await btn.click();
        await shotSection(page, item.file);
        const showAll = page.getByRole("button", { name: "Show all" });
        if ((await showAll.count()) > 0) await showAll.click();
      } else {
        await shotSection(page, item.file);
      }
    }

    await page.setViewportSize({ width: 390, height: 844 });
    await page.locator("#cross-city").scrollIntoViewIfNeeded();
    await shotSection(page, "cross-city-real-mobile");

    for (const name of REAL_SHOTS) {
      expect(existsSync(path.join(SHOT_DIR, `${name}.png`))).toBeTruthy();
    }
  });
});
