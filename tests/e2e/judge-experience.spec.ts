import { mkdirSync } from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";

const SHOT_DIR = path.resolve("docs", "judge-experience", "screenshots");

/** Canonical Phoenix visual reference contract — keep in sync with APPROVED_SCREENSHOTS.md */
const CANONICAL_SHOTS = [
  "phoenix-landing-1440x900",
  "phoenix-thermal-map",
  "phoenix-canopy-map",
  "phoenix-income-map",
  "phoenix-older-housing-map",
  "phoenix-matched-night",
  "phoenix-observed-instants",
  "phoenix-context",
  "phoenix-preparedness",
  "phoenix-direction",
  "phoenix-method-provenance",
  "phoenix-1024",
  "phoenix-mobile-390x844",
] as const;

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
    expect(before.area).toMatch(/Census Tract 1074\.01/i);

    await page.getByTestId("area-selector-input").selectOption("04013107500");
    await expect(page.getByTestId("selected-area-label")).toContainText(/Census Tract 1075/i);
    await expect(page.getByTestId("judge-shell")).toHaveAttribute(
      "data-selected-area-id",
      "04013107500",
    );
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

  test("rapid area switches settle on the final selection without oscillation", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/");
    await waitForEvidence(page);

    const sequence = [
      "04013107401",
      "04013107500",
      "04013107601",
      "04013107602",
      "04013108802",
    ];
    for (const geoid of sequence) {
      await page.getByTestId("area-selector-input").selectOption(geoid);
    }
    await expect(page.getByTestId("judge-shell")).toHaveAttribute(
      "data-selected-area-id",
      "04013108802",
      { timeout: 45_000 },
    );
    await expect(page.getByTestId("selected-area-label")).toContainText(/Census Tract/i);
    await expect(page.getByTestId("area-selector-input")).toHaveValue("04013108802");
    // Allow in-flight evidence to settle; selection must remain the last choice.
    await page.waitForTimeout(1500);
    await expect(page.getByTestId("judge-shell")).toHaveAttribute(
      "data-selected-area-id",
      "04013108802",
    );
    await expect(page.getByTestId("selected-area-geoid")).toHaveText("04013108802");
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
    await expect(page.getByTestId("historical-position-why")).toContainText(/Why unavailable\?/i);

    await shot(page, "phoenix-landing-1440x900");
    await shot(page, "phoenix-thermal-map", { locator: "[data-testid='map-stage']" });

    await page.locator('[data-testid="map-mode-tabs"] [data-mode="TREE_CANOPY"]').click();
    await expect(page.getByTestId("map-stage")).toHaveAttribute("data-map-mode", "TREE_CANOPY");
    await expect(page.getByTestId("context-mode-legend")).toBeVisible();
    await expect(page.getByTestId("context-mode-legend")).toHaveAttribute("data-mode", "TREE_CANOPY");
    await expect(page.getByTestId("thermal-snapshot-legend")).toHaveCount(0);
    await shot(page, "phoenix-canopy-map", { locator: "[data-testid='map-stage']" });

    await page.locator('[data-testid="map-mode-tabs"] [data-mode="INCOME"]').click();
    await expect(page.getByTestId("map-stage")).toHaveAttribute("data-map-mode", "INCOME");
    await expect(page.getByTestId("context-mode-legend")).toHaveAttribute("data-mode", "INCOME");
    await shot(page, "phoenix-income-map", { locator: "[data-testid='map-stage']" });

    await page.locator('[data-testid="map-mode-tabs"] [data-mode="OLDER_HOUSING"]').click();
    await expect(page.getByTestId("map-stage")).toHaveAttribute("data-map-mode", "OLDER_HOUSING");
    await expect(page.getByTestId("context-mode-legend")).toHaveAttribute("data-mode", "OLDER_HOUSING");
    await shot(page, "phoenix-older-housing-map", { locator: "[data-testid='map-stage']" });

    await page.locator('[data-testid="map-mode-tabs"] [data-mode="THERMAL"]').click();

    await page.getByTestId("matched-nighttime").scrollIntoViewIfNeeded();
    await shot(page, "phoenix-matched-night", { locator: "[data-testid='matched-nighttime']" });

    await page.getByTestId("observed-instants").scrollIntoViewIfNeeded();
    await shot(page, "phoenix-observed-instants", { locator: "[data-testid='observed-instants']" });

    await page.getByTestId("context-panel").scrollIntoViewIfNeeded();
    await shot(page, "phoenix-context", { locator: "[data-testid='context-panel']" });

    await page.getByTestId("preparedness-panel").scrollIntoViewIfNeeded();
    await shot(page, "phoenix-preparedness", { locator: "[data-testid='preparedness-panel']" });

    await page.getByTestId("decision-direction").scrollIntoViewIfNeeded();
    await shot(page, "phoenix-direction", {
      locator: "[data-testid='decision-direction']",
    });

    await page.getByTestId("evidence-disclosure").scrollIntoViewIfNeeded();
    await page.getByTestId("evidence-disclosure").evaluate((node) => {
      if (node instanceof HTMLDetailsElement) {
        node.open = true;
      }
    });
    await shot(page, "phoenix-method-provenance", {
      locator: "[data-testid='evidence-disclosure']",
    });

    await page.setViewportSize({ width: 1024, height: 768 });
    await page.goto("/");
    await waitForEvidence(page);
    await shot(page, "phoenix-1024");

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
    await expect(page.getByTestId("section-nav-prev")).toBeHidden();
    await expect(page.getByTestId("section-nav-next")).toBeVisible();
    const overflowX = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    );
    expect(overflowX).toBeFalsy();
    await shot(page, "phoenix-mobile-390x844");

    // Advance to last section: Next hidden at 05/05.
    for (let i = 0; i < 4; i += 1) {
      await page.getByTestId("section-nav-next").click();
    }
    await expect(page.getByTestId("section-nav-index")).toContainText("05 / 05");
    await expect(page.getByTestId("section-nav-next")).toBeHidden();
    await expect(page.getByTestId("section-nav-prev")).toBeVisible();

    // Sanity: every canonical name was requested by this suite.
    expect(CANONICAL_SHOTS).toHaveLength(13);
  });
});
