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

async function waitForCrossCity(page: Page) {
  await expect(page.getByTestId("judge-shell")).toBeVisible({ timeout: 60_000 });
  await page.locator("#cross-city").scrollIntoViewIfNeeded();
  await expect(page.getByTestId("cross-city-section")).toBeVisible({ timeout: 60_000 });
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

    await page.getByTestId("cross-city-fill-temperature").click();
    await expect(page.getByTestId("cross-city-fill-temperature")).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await shotSection(page, "cross-city-real-temperature-fill");
    await page.getByTestId("cross-city-fill-canopy").click();

    // Tooltip / hover evidence
    const bubble = page.locator("[data-testid='cross-city-bubble-explorer'] circle").first();
    await bubble.hover({ force: true });
    await expect(page.getByTestId("cross-city-tooltip")).toBeVisible();
    await shotSection(page, "cross-city-real-tooltip");

    const isolates: Array<{ label: string; file: string }> = [
      { label: "Only show Phoenix, AZ", file: "cross-city-real-phoenix-isolated" },
      { label: "Only show Los Angeles, CA", file: "cross-city-real-los-angeles-isolated" },
      { label: "Only show Las Vegas, NV", file: "cross-city-real-las-vegas-isolated" },
      { label: "Only show Tucson, AZ", file: "cross-city-real-tucson-isolated" },
    ];
    for (const item of isolates) {
      await page.getByRole("button", { name: item.label }).click();
      await shotSection(page, item.file);
      await page.getByRole("button", { name: "Show all" }).click();
    }

    await page.setViewportSize({ width: 390, height: 844 });
    await page.locator("#cross-city").scrollIntoViewIfNeeded();
    await shotSection(page, "cross-city-real-mobile");

    for (const name of REAL_SHOTS) {
      expect(existsSync(path.join(SHOT_DIR, `${name}.png`))).toBeTruthy();
    }
  });
});
