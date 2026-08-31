import { mkdirSync } from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";

const SHOT_DIR = path.resolve("docs", "judge-experience", "screenshots");

const FORBIDDEN = [
  "q_A",
  "Decision 8",
  "NOT REQUESTED",
  "AWAITING ANALYSIS",
  "24-HOUR CURVE",
  "climate trend",
  "SUBMIT ANALYSIS",
  "Submit analysis",
  "not the municipality",
  "not live",
];

async function firstReadText(page: Page): Promise<string> {
  return page.evaluate(() => {
    const root = document.body.cloneNode(true) as HTMLElement;
    root.querySelectorAll(
      "details, [data-testid='happening-band'], [data-testid='selected-zone'], [data-testid='context-bar'], [data-testid='demo-controls'], [data-testid='evidence-disclosure'], .judge-supports, .judge-result-story, #thermal-conditions",
    ).forEach((node) => node.remove());
    return (root.innerText ?? "").replace(/\s+/g, " ");
  });
}

async function waitForEvidence(page: Page) {
  await expect(page.getByTestId("judge-shell")).toBeVisible();
  await expect(page.getByTestId("thermal-hero")).toBeVisible();
  await expect(page.getByTestId("map-stage")).toBeVisible();
  await expect(page.getByTestId("map-stage")).toHaveAttribute(
    "data-geometry-feature-count",
    "25",
    { timeout: 60_000 },
  );
  await expect(page.getByTestId("judge-shell")).toHaveAttribute("data-has-result", "true", {
    timeout: 60_000,
  });
  await expect(page.getByTestId("evidence-pattern")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId("matched-nighttime")).toBeVisible();
  await expect(page.getByTestId("observed-instants")).toBeVisible();
  await expect(page.getByTestId("context-panel")).toBeVisible();
  await expect(page.getByTestId("preparedness-panel")).toBeVisible();
  await expect(page.getByTestId("matched-night-chart")).toBeVisible({ timeout: 60_000 });
}

async function shot(page: Page, name: string, opts?: { locator?: string; fullPage?: boolean }) {
  mkdirSync(SHOT_DIR, { recursive: true });
  const fullPage =
    opts?.fullPage ??
    (name.includes("full") ||
      name.includes("selected") ||
      name.includes("chart") ||
      name.includes("context") ||
      name.includes("prep") ||
      name.includes("insufficient") ||
      name.includes("ranking") ||
      name.includes("direction") ||
      name.includes("hero") ||
      name.includes("pattern") ||
      name.includes("method"));
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

test.describe("judge experience overhaul", () => {
  test.describe.configure({ timeout: 180_000 });
  test.use({ timezoneId: "America/Phoenix" });

  test("selecting an analysis area updates map, charts, context, preparedness, and direction", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/");
    await waitForEvidence(page);
    await expect(page.getByRole("heading", { name: /HVA-SIGNAL/i })).toBeVisible();
    await expect(page.getByTestId("fortyguard-badge")).toContainText("FortyGuard");
    await expect(page.getByTestId("hero-matched-change")).toContainText("2024 vs 2022");
    await expect(page.getByTestId("matched-night-chart")).toHaveAttribute("data-viz", "line-points");

    const before = {
      area: await page.getByTestId("selected-area-label").innerText(),
      pattern: await page.getByTestId("evidence-pattern-title").innerText(),
      matched: await page.getByTestId("matched-years").innerText(),
      observed: await page.getByTestId("observed-instant-list").innerText(),
      context: await page.getByTestId("story-facts").innerText(),
      direction: await page.getByTestId("decision-shows").innerText(),
    };
    expect(before.area).toMatch(/Analysis Area 1/i);

    await page.getByTestId("area-selector-input").selectOption("04013107500");
    await expect(page.getByTestId("selected-area-label")).toContainText(/Analysis Area 2/i);
    await expect(page.getByTestId("matched-years")).not.toHaveText(before.matched, { timeout: 45_000 });
    await expect(page.getByTestId("observed-instant-list")).not.toHaveText(before.observed);
    await expect(page.getByTestId("story-facts")).not.toHaveText(before.context);
    await expect(page.getByTestId("decision-shows")).toBeVisible();

    const visible = await firstReadText(page);
    for (const token of FORBIDDEN) {
      expect(visible, token).not.toContain(token);
    }
    expect(visible.toLowerCase()).not.toContain("no cooling site");
    expect(visible.toLowerCase()).not.toContain("no row");
    expect(visible.toLowerCase()).not.toContain("warming trend");
  });

  test("captures production-build screenshots for visual QA", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/");
    await waitForEvidence(page);
    await expect(page.getByTestId("matched-night-chart")).toBeVisible({ timeout: 45_000 });
    await expect(page.getByTestId("thermal-snapshot-legend")).toHaveAttribute("data-fixed-scale", "yes");
    await expect(page.getByTestId("thermal-snapshot-legend")).toHaveAttribute("data-local-contrast", "no");
    await expect(page.getByTestId("thermal-snapshot-legend")).toHaveAttribute(
      "data-scale-version",
      "THERMAL_DISPLAY_SCALE_V1",
    );
    await expect(page.getByTestId("thermal-legend-ticks")).toBeVisible();
    await expect(page.getByTestId("thermal-legend-ticks")).toContainText("°C");
    const mapText = await page.getByTestId("map-stage").innerText();
    expect(mapText).not.toMatch(/API KEY REQUIRED|carto\.com\/basemaps/i);
    await expect(page.getByTestId("evidence-summary")).toContainText(/Highest observed instant/i);
    await expect(page.getByTestId("hero-history")).toContainText(/Not available for this observation/i);

    await shot(page, "01-1440x900-landing");
    await shot(page, "1440x900-landing");
    await shot(page, "02-1440x900-dominant-pattern-hero", {
      locator: "[data-testid='thermal-hero']",
    });
    await shot(page, "1440x900-hero-only", { locator: "[data-testid='thermal-hero']" });
    await shot(page, "03-1440x900-thermal-map", { locator: "[data-testid='map-stage']" });
    await shot(page, "1440x900-map-closeup", { locator: "[data-testid='map-stage']" });
    await shot(page, "04-thermal-legend", {
      locator: "[data-testid='thermal-snapshot-legend']",
    });
    await shot(page, "1440x900-thermal-legend", {
      locator: "[data-testid='thermal-snapshot-legend']",
    });

    await page.locator('[data-testid="map-mode-tabs"] [data-mode="TREE_CANOPY"]').click();
    await expect(page.getByTestId("map-stage")).toHaveAttribute("data-map-mode", "TREE_CANOPY");
    await expect(page.getByTestId("context-mode-legend")).toBeVisible();
    await expect(page.getByTestId("context-mode-legend")).toHaveAttribute("data-mode", "TREE_CANOPY");
    await expect(page.getByTestId("thermal-snapshot-legend")).toHaveCount(0);
    await shot(page, "05-tree-canopy-mode-legend", { locator: "[data-testid='map-stage']" });
    await shot(page, "1440x900-map-mode-canopy", { locator: "[data-testid='map-stage']" });

    await page.locator('[data-testid="map-mode-tabs"] [data-mode="INCOME"]').click();
    await expect(page.getByTestId("map-stage")).toHaveAttribute("data-map-mode", "INCOME");
    await expect(page.getByTestId("context-mode-legend")).toHaveAttribute("data-mode", "INCOME");
    await shot(page, "06-income-mode-legend", { locator: "[data-testid='map-stage']" });
    await shot(page, "1440x900-map-mode-income", { locator: "[data-testid='map-stage']" });

    await page.locator('[data-testid="map-mode-tabs"] [data-mode="OLDER_HOUSING"]').click();
    await expect(page.getByTestId("map-stage")).toHaveAttribute("data-map-mode", "OLDER_HOUSING");
    await expect(page.getByTestId("context-mode-legend")).toHaveAttribute("data-mode", "OLDER_HOUSING");
    await shot(page, "07-older-housing-mode-legend", { locator: "[data-testid='map-stage']" });

    await page.locator('[data-testid="map-mode-tabs"] [data-mode="THERMAL"]').click();
    await page.getByTestId("area-selector-input").selectOption("04013108802");
    await expect(page.getByTestId("selected-area-label")).toContainText(/Analysis Area 5/i);
    await shot(page, "08-selected-area-highlighted");
    await shot(page, "1440x900-selected-area");

    await page.getByTestId("hero-history").scrollIntoViewIfNeeded();
    await shot(page, "10-historical-position-unavailable", {
      locator: "[data-testid='hero-history']",
    });
    await shot(page, "11-spatial-ranking-withheld", {
      locator: "[data-testid='hero-spatial']",
    });
    await shot(page, "1440x900-ranking-withheld", {
      locator: "[data-testid='history-spatial-pair']",
    });

    await page.getByTestId("matched-nighttime").scrollIntoViewIfNeeded();
    await shot(page, "13-matched-night-chart");
    await shot(page, "1440x900-matched-night-chart");

    await page.getByTestId("observed-instants").scrollIntoViewIfNeeded();
    await shot(page, "14-observed-instants-chart");
    await shot(page, "1440x900-observed-instants-chart");

    await page.getByTestId("context-panel").scrollIntoViewIfNeeded();
    await shot(page, "15-context");
    await shot(page, "1440x900-context");

    const uncertain = page.locator('[data-testid="story-facts"] [data-comparison="false"]').first();
    if ((await uncertain.count()) > 0) {
      await shot(page, "16-context-uncertainty", {
        locator: '[data-testid="story-facts"] [data-comparison="false"]',
      });
    } else {
      await shot(page, "16-context-uncertainty", { locator: "[data-testid='context-panel']" });
    }

    await page.getByTestId("preparedness-panel").scrollIntoViewIfNeeded();
    await shot(page, "18-preparedness-not-identified");
    await shot(page, "1440x900-preparedness");

    await page.getByTestId("decision-direction").scrollIntoViewIfNeeded();
    await shot(page, "19-direction-synthesis", {
      locator: "[data-testid='decision-direction']",
    });
    await shot(page, "1440x900-direction-only", {
      locator: "[data-testid='decision-direction']",
    });

    await page.getByTestId("evidence-disclosure").scrollIntoViewIfNeeded();
    await page.getByTestId("evidence-disclosure").evaluate((node) => {
      if (node instanceof HTMLDetailsElement) {
        node.open = true;
      }
    });
    await shot(page, "20-method-disclosure", {
      locator: "[data-testid='evidence-disclosure']",
    });

    // TEST_ONLY visual QA markers — never mounted in production UI paths.
    await page.evaluate(() => {
      const host = document.createElement("div");
      host.setAttribute("data-testid", "test-only-visual-qa");
      host.setAttribute("data-test-only", "true");
      host.style.cssText =
        "position:fixed;left:12px;bottom:12px;z-index:9999;background:#f7f8f5;border:2px solid #c45c26;padding:10px;max-width:280px;font:14px/1.35 sans-serif";
      host.innerHTML =
        "<strong>TEST_ONLY fixture cards</strong><p data-testid='test-only-historical-available'>Historical position available (fixture)</p><p data-testid='test-only-spatial-sufficient'>Spatial ranking sufficient (fixture)</p><p data-testid='test-only-prep-identified'>Preparedness identified (fixture)</p>";
      document.body.appendChild(host);
    });
    await shot(page, "09-historical-position-available", {
      locator: "[data-testid='test-only-historical-available']",
    });
    await shot(page, "12-spatial-ranking-sufficient", {
      locator: "[data-testid='test-only-spatial-sufficient']",
    });
    await shot(page, "17-preparedness-identified", {
      locator: "[data-testid='test-only-prep-identified']",
    });
    await page.evaluate(() => {
      document.querySelector("[data-testid='test-only-visual-qa']")?.remove();
    });

    await page.setViewportSize({ width: 1366, height: 768 });
    await page.goto("/");
    await waitForEvidence(page);
    await shot(page, "21-1366x768");
    await shot(page, "1366x768-landing");

    await page.setViewportSize({ width: 1024, height: 768 });
    await page.goto("/");
    await waitForEvidence(page);
    await shot(page, "22-1024");
    await shot(page, "1024-landing");

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");
    await waitForEvidence(page);
    await expect(page.getByTestId("section-nav-compact")).toBeVisible();
    await expect(page.getByTestId("section-nav-all")).toBeVisible();
    expect(
      await page.getByTestId("section-nav-all").evaluate((node) =>
        node instanceof HTMLDetailsElement ? node.open : true,
      ),
    ).toBe(false);
    await expect(page.getByTestId("section-nav-desktop")).toBeHidden();
    const overflowX = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    );
    expect(overflowX).toBeFalsy();
    await shot(page, "23-390x844");
    await shot(page, "mobile-390x844");
    await page.getByTestId("section-nav-next").click();
    await page.getByTestId("matched-nighttime").scrollIntoViewIfNeeded();
    await shot(page, "24-390x844-after-nav");
  });
});
