/**
 * Phase 0 baseline screenshots for pre-final HVA product pass.
 * Captures recovery reference at protected SHA before substantive UI edits.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";

const SHOT_DIR = path.resolve("docs", "release", "pre-final-ui-baseline");
const BASELINE_SHA = "6bfde4afd081386d16aa900093e251d27a0f312b";

type Shot = {
  file: string;
  viewport: { width: number; height: number };
  screen: string;
  expected: string[];
};

const SHOTS: Shot[] = [
  {
    file: "explore-phoenix-1440x900",
    viewport: { width: 1440, height: 900 },
    screen: "Explore Phoenix",
    expected: ["workspace-header", "explore-city", "map-stage", "zone-panel", "city-selector"],
  },
  {
    file: "explore-phoenix-1366x768",
    viewport: { width: 1366, height: 768 },
    screen: "Explore Phoenix laptop",
    expected: ["workspace-header", "explore-city", "map-stage", "zone-panel"],
  },
  {
    file: "explore-phoenix-1024",
    viewport: { width: 1024, height: 768 },
    screen: "Explore Phoenix 1024",
    expected: ["workspace-header", "explore-city", "map-stage", "zone-panel"],
  },
  {
    file: "explore-phoenix-mobile",
    viewport: { width: 390, height: 844 },
    screen: "mobile Explore",
    expected: ["workspace-header", "explore-city", "map-stage"],
  },
  {
    file: "explore-las-vegas-1440x900",
    viewport: { width: 1440, height: 900 },
    screen: "Explore Las Vegas",
    expected: ["explore-city", "map-stage", "zone-panel"],
  },
  {
    file: "explore-phoenix-tree-canopy-1440x900",
    viewport: { width: 1440, height: 900 },
    screen: "tree canopy",
    expected: ["map-stage", "map-mode-tabs"],
  },
  {
    file: "explore-phoenix-selected-zone-1440x900",
    viewport: { width: 1440, height: 900 },
    screen: "selected Zone",
    expected: ["zone-panel", "zone-name", "zone-temp"],
  },
  {
    file: "compare-cities-1440x900",
    viewport: { width: 1440, height: 900 },
    screen: "Compare Cities",
    expected: ["compare-cities", "cross-city-section", "cross-city-bubble-explorer"],
  },
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

async function shot(page: Page, name: string) {
  mkdirSync(SHOT_DIR, { recursive: true });
  await page.screenshot({
    path: path.join(SHOT_DIR, `${name}.png`),
    animations: "disabled",
  });
}

test.describe("pre-final UI baseline screenshots", () => {
  test.describe.configure({ timeout: 240_000 });
  test.use({ timezoneId: "America/Phoenix" });

  test("captures baseline recovery screenshots + MANIFEST", async ({ page }) => {
    const manifestLines: string[] = [
      `# Pre-final UI baseline MANIFEST`,
      ``,
      `- baseline_sha: \`${BASELINE_SHA}\``,
      `- captured_at: ${new Date().toISOString()}`,
      `- contract: docs/release/CORE_UI_CONTRACT.json`,
      ``,
      `| File | Viewport | Screen/state | Expected major elements |`,
      `|------|----------|--------------|-------------------------|`,
    ];

    // Phoenix landing 1440
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/");
    await waitForWorkspaceMap(page);
    await expect(page.getByTestId("map-stage")).toHaveAttribute("data-map-state", "sufficient", {
      timeout: 60_000,
    });
    await shot(page, "explore-phoenix-1440x900");

    // laptop / 1024 / mobile phoenix
    for (const s of ["explore-phoenix-1366x768", "explore-phoenix-1024", "explore-phoenix-mobile"] as const) {
      const meta = SHOTS.find((x) => x.file === s)!;
      await page.setViewportSize(meta.viewport);
      await page.waitForTimeout(300);
      await shot(page, s);
    }

    // restore desktop for remaining shots
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.waitForTimeout(300);

    // Las Vegas
    const citySelect = page.getByTestId("city-selector").locator("select");
    await citySelect.selectOption("las-vegas-nv");
    await expect(page.getByTestId("explore-city")).toHaveAttribute("data-city", "las-vegas-nv");
    await expect(page.getByTestId("map-stage")).toBeVisible();
    await page.waitForTimeout(800);
    await shot(page, "explore-las-vegas-1440x900");

    // back to Phoenix + tree canopy
    await citySelect.selectOption("phoenix-az");
    await expect(page.getByTestId("explore-city")).toHaveAttribute("data-city", "phoenix-az");
    await expect(page.getByTestId("map-stage")).not.toHaveAttribute(
      "data-geometry-feature-count",
      "0",
      { timeout: 60_000 },
    );
    const canopyTab = page.locator('[data-testid="map-mode-tabs"] [data-mode="TREE_CANOPY"]');
    await canopyTab.click();
    await page.waitForTimeout(400);
    await shot(page, "explore-phoenix-tree-canopy-1440x900");

    // selected zone panel focus
    await expect(page.getByTestId("zone-panel")).toBeVisible();
    await shot(page, "explore-phoenix-selected-zone-1440x900");

    // Compare Cities
    await page.getByTestId("mode-compare").click();
    await expect(page.getByTestId("compare-cities")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("cross-city-section")).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId("cross-city-bubble-explorer")).toBeVisible({
      timeout: 60_000,
    });
    await shot(page, "compare-cities-1440x900");

    for (const s of SHOTS) {
      manifestLines.push(
        `| \`${s.file}.png\` | ${s.viewport.width}×${s.viewport.height} | ${s.screen} | ${s.expected.join(", ")} |`,
      );
    }
    manifestLines.push("");
    writeFileSync(path.join(SHOT_DIR, "MANIFEST.md"), manifestLines.join("\n"), "utf8");
  });
});
