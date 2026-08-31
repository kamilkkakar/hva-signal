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
      name.includes("hero"));
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
  test.describe.configure({ timeout: 120_000 });
  test.use({ timezoneId: "America/Phoenix" });

  test("selecting an analysis area updates map, charts, context, and preparedness", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/");
    await waitForEvidence(page);
    await expect(page.getByRole("heading", { name: /HVA-SIGNAL/i })).toBeVisible();
    await expect(page.getByTestId("fortyguard-badge")).toContainText("FortyGuard");
    await expect(page.getByTestId("source-banner")).toContainText("REPLAY");

    await expect(page.getByTestId("matched-night-chart")).toBeVisible({ timeout: 45_000 });
    await expect(page.getByTestId("observed-instants-chart")).toBeVisible();
    await expect(page.getByTestId("selected-area-story")).toBeVisible();
    await expect(page.getByTestId("preparedness-status")).toBeVisible();

    const before = {
      area: await page.getByTestId("selected-area-label").innerText(),
      temp: await page.getByTestId("hero-temperature").innerText(),
      matched: await page.getByTestId("matched-years").innerText(),
      observed: await page.getByTestId("observed-instant-list").innerText(),
      context: await page.getByTestId("story-facts").innerText(),
      prep: await page.getByTestId("story-support").innerText(),
    };
    expect(before.area).toMatch(/Analysis Area 1/i);

    await page.getByTestId("area-selector-input").selectOption("04013107500");
    await expect(page.getByTestId("selected-area-label")).toContainText(/Analysis Area 2/i);
    await expect(page.getByTestId("map-stage")).toBeVisible();

    await expect(page.getByTestId("matched-years")).not.toHaveText(before.matched, { timeout: 45_000 });
    await expect(page.getByTestId("observed-instant-list")).not.toHaveText(before.observed);
    await expect(page.getByTestId("story-facts")).not.toHaveText(before.context);

    const afterPrep = await page.getByTestId("story-support").innerText();
    expect(afterPrep.length).toBeGreaterThan(10);
    expect(`${before.area}${before.matched}${before.observed}${before.context}`).not.toEqual(
      `${await page.getByTestId("selected-area-label").innerText()}${await page.getByTestId("matched-years").innerText()}${await page.getByTestId("observed-instant-list").innerText()}${await page.getByTestId("story-facts").innerText()}`,
    );

    const visible = await firstReadText(page);
    for (const token of FORBIDDEN) {
      expect(visible, token).not.toContain(token);
    }
    expect(visible.toLowerCase()).not.toContain("no cooling site");
  });

  test("captures production-build screenshots for visual QA", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/");
    await waitForEvidence(page);
    await expect(page.getByTestId("matched-night-chart")).toBeVisible({ timeout: 45_000 });
    await shot(page, "1440x900-landing");

    await shot(page, "1440x900-map-closeup", { locator: "[data-testid='map-stage']" });
    await shot(page, "1440x900-thermal-legend", {
      locator: "[data-testid='thermal-snapshot-legend']",
    });
    await shot(page, "1440x900-hero-only", { locator: "[data-testid='thermal-hero']" });

    await page.locator('[data-testid="map-mode-tabs"] [data-mode="TREE_CANOPY"]').click();
    await expect(page.getByTestId("map-stage")).toHaveAttribute("data-map-mode", "TREE_CANOPY");
    await shot(page, "1440x900-map-mode-canopy", { locator: "[data-testid='map-stage']" });

    await page.locator('[data-testid="map-mode-tabs"] [data-mode="INCOME"]').click();
    await expect(page.getByTestId("map-stage")).toHaveAttribute("data-map-mode", "INCOME");
    await shot(page, "1440x900-map-mode-income", { locator: "[data-testid='map-stage']" });

    await page.locator('[data-testid="map-mode-tabs"] [data-mode="THERMAL"]').click();

    await page.getByTestId("area-selector-input").selectOption("04013108802");
    await expect(page.getByTestId("selected-area-label")).toContainText(/Analysis Area 5/i);
    await expect(page.getByTestId("matched-night-chart")).toBeVisible();
    await shot(page, "1440x900-selected-area");

    await page.getByTestId("matched-nighttime").scrollIntoViewIfNeeded();
    await shot(page, "1440x900-matched-night-chart");

    await page.getByTestId("observed-instants").scrollIntoViewIfNeeded();
    await shot(page, "1440x900-observed-instants-chart");

    await page.getByTestId("context-panel").scrollIntoViewIfNeeded();
    await shot(page, "1440x900-context");

    await page.getByTestId("preparedness-panel").scrollIntoViewIfNeeded();
    await shot(page, "1440x900-preparedness");

    await page.getByTestId("decision-direction").scrollIntoViewIfNeeded();
    await shot(page, "1440x900-direction-only", { locator: "[data-testid='decision-direction']" });

    await page.getByTestId("evidence-summary").scrollIntoViewIfNeeded();
    await shot(page, "1440x900-ranking-withheld");
    await shot(page, "1440x900-insufficient-evidence");

    await page.setViewportSize({ width: 1366, height: 768 });
    await page.goto("/");
    await waitForEvidence(page);
    await shot(page, "1366x768-landing");

    await page.setViewportSize({ width: 1024, height: 768 });
    await page.goto("/");
    await waitForEvidence(page);
    await shot(page, "1024-landing");

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");
    await waitForEvidence(page);
    const overflowX = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    );
    expect(overflowX).toBeFalsy();
    await shot(page, "mobile-390x844");
  });
});
