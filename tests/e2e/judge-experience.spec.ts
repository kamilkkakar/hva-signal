import { mkdirSync } from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";

const SHOT_DIR = path.resolve("docs", "judge-experience", "screenshots");

const CANONICAL_SHOTS = [
  "phoenix-landing-1440x900",
  "phoenix-thermal-map",
  "phoenix-canopy-map",
  "phoenix-income-map",
  "phoenix-older-housing-map",
  "phoenix-zone-panel",
  "phoenix-1024",
  "phoenix-mobile-390x844",
] as const;

const FORBIDDEN = [
  "q_A",
  "NOT REQUESTED",
  "AWAITING ANALYSIS",
  "24-HOUR CURVE",
  "climate trend",
  "SUBMIT ANALYSIS",
  "Submit analysis",
  "not the municipality",
  "not live",
];

async function waitForWorkspaceMap(page: Page) {
  await expect(page.getByTestId("workspace")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("explore-city")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("map-stage")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("map-stage")).not.toHaveAttribute(
    "data-geometry-feature-count",
    "0",
    { timeout: 60_000 },
  );
}

async function shot(page: Page, name: string, opts?: { locator?: string; fullPage?: boolean }) {
  mkdirSync(SHOT_DIR, { recursive: true });
  const fullPage = opts?.fullPage ?? false;
  if (opts?.locator) {
    await page.locator(opts.locator).screenshot({
      path: path.join(SHOT_DIR, `${name}.png`),
      animations: "disabled",
    });
    return;
  }
  await page.screenshot({
    path: path.join(SHOT_DIR, `${name}.png`),
    fullPage,
    animations: "disabled",
  });
}

test.describe("workspace experience", () => {
  test.describe.configure({ timeout: 180_000 });
  test.use({ timezoneId: "America/Phoenix" });

  test("city selector switches cities and map reloads geometry", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/");
    await waitForWorkspaceMap(page);

    await expect(page.getByTestId("city-selector")).toBeVisible();
    const citySelect = page.getByTestId("city-selector").locator("select");

    await expect(page.getByTestId("explore-city")).toHaveAttribute("data-city", "phoenix-az");

    await citySelect.selectOption("las-vegas-nv");
    await expect(page.getByTestId("explore-city")).toHaveAttribute("data-city", "las-vegas-nv");
    await expect(page.getByTestId("map-stage")).toBeVisible();

    await citySelect.selectOption("tucson-az");
    await expect(page.getByTestId("explore-city")).toHaveAttribute("data-city", "tucson-az");

    await citySelect.selectOption("los-angeles-ca");
    await expect(page.getByTestId("explore-city")).toHaveAttribute("data-city", "los-angeles-ca");

    await citySelect.selectOption("phoenix-az");
    await expect(page.getByTestId("explore-city")).toHaveAttribute("data-city", "phoenix-az");
    await expect(page.getByTestId("map-stage")).not.toHaveAttribute(
      "data-geometry-feature-count",
      "0",
      { timeout: 60_000 },
    );
  });

  test("zone naming uses Census Tract terminology", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/");
    await waitForWorkspaceMap(page);
    await expect(page.getByTestId("zone-panel")).toBeVisible();
    const zoneName = await page.getByTestId("zone-name").textContent();
    expect(zoneName).toMatch(/Zone\s+\d/);
    const secondary = page.getByTestId("zone-secondary");
    if ((await secondary.count()) > 0) {
      await expect(secondary).toContainText("Census Tract");
    }
  });

  test("captures production-build screenshots for visual QA", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/");
    await waitForWorkspaceMap(page);
    await expect(page.getByRole("heading", { name: /HVA-SIGNAL/i })).toBeVisible();

    const map = page.getByTestId("map-stage");
    await expect(map).toHaveAttribute("data-map-state", "sufficient", {
      timeout: 60_000,
    });

    await shot(page, "phoenix-landing-1440x900");
    await shot(page, "phoenix-thermal-map", { locator: "[data-testid='map-stage']" });

    const canopyTab = page.locator('[data-testid="map-mode-tabs"] [data-mode="TREE_CANOPY"]');
    if ((await canopyTab.count()) > 0) {
      await canopyTab.click();
      await expect(map).toHaveAttribute("data-map-mode", "TREE_CANOPY");
      await shot(page, "phoenix-canopy-map", { locator: "[data-testid='map-stage']" });
    }

    const incomeTab = page.locator('[data-testid="map-mode-tabs"] [data-mode="INCOME"]');
    if ((await incomeTab.count()) > 0) {
      await incomeTab.click();
      await expect(map).toHaveAttribute("data-map-mode", "INCOME");
      await shot(page, "phoenix-income-map", { locator: "[data-testid='map-stage']" });
    }

    const housingTab = page.locator('[data-testid="map-mode-tabs"] [data-mode="OLDER_HOUSING"]');
    if ((await housingTab.count()) > 0) {
      await housingTab.click();
      await expect(map).toHaveAttribute("data-map-mode", "OLDER_HOUSING");
      await shot(page, "phoenix-older-housing-map", { locator: "[data-testid='map-stage']" });
    }

    const thermalTab = page.locator('[data-testid="map-mode-tabs"] [data-mode="THERMAL"]');
    if ((await thermalTab.count()) > 0) {
      await thermalTab.click();
    }

    await shot(page, "phoenix-zone-panel", { locator: "[data-testid='zone-panel']" });

    await page.setViewportSize({ width: 1024, height: 768 });
    await page.goto("/");
    await waitForWorkspaceMap(page);
    await shot(page, "phoenix-1024");

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");
    await waitForWorkspaceMap(page);
    const overflowX = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    );
    expect(overflowX).toBeFalsy();
    await shot(page, "phoenix-mobile-390x844");

    expect(CANONICAL_SHOTS).toHaveLength(8);
  });

  test("first-read text has no forbidden phrases", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/");
    await waitForWorkspaceMap(page);

    const visible = await page.evaluate(() => {
      return (document.body.innerText ?? "").replace(/\s+/g, " ");
    });
    for (const token of FORBIDDEN) {
      expect(visible, token).not.toContain(token);
    }
    expect(visible.toLowerCase()).not.toContain("no cooling site");
    expect(visible.toLowerCase()).not.toContain("no row");
  });

  test("public observation mode is Published-only until bounded live is verified", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/");
    await waitForWorkspaceMap(page);

    await expect(page.getByTestId("observation-published-only")).toBeVisible();
    await expect(page.getByTestId("observation-published-only")).toContainText("Published");
    await expect(page.getByTestId("obs-live")).toHaveCount(0);
    await expect(page.getByTestId("live-controls")).toHaveCount(0);
    await expect(page.getByTestId("run-live")).toHaveCount(0);
  });
});
