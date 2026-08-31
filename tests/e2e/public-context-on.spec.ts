import { expect, test, type Page } from "@playwright/test";

const CONTEXT_ON = /^(1|true|yes|on)$/i.test(
  (process.env.HVA_PUBLIC_CONTEXT ?? "").trim(),
);

const INSUFFICIENT_TIME = "2022-07-01T03:00";

const STORY_QUESTIONS = [
  "What local context matters?",
  "What support is identified?",
] as const;

async function openDetails(page: Page, testId: string) {
  const details = page.getByTestId(testId);
  if ((await details.count()) === 0) {
    return;
  }
  await details.evaluate((node) => {
    if (node instanceof HTMLDetailsElement) {
      node.open = true;
    }
  });
}

async function openDemoControls(page: Page) {
  await openDetails(page, "demo-controls");
}

async function openEvidenceDisclosure(page: Page) {
  await openDetails(page, "evidence-disclosure");
}

async function fillAnalysisTime(page: Page, value: string) {
  await openDemoControls(page);
  const input = page.locator('input[name="analysis_time"]');
  await input.fill(value);
  await expect(input).toHaveValue(value);
}

async function submitAnalysis(page: Page) {
  await openDemoControls(page);
  await page.getByRole("button", { name: "Submit analysis" }).click();
}

async function openMapAdvancedChrome(page: Page) {
  const wrap = page.getByTestId("map-advanced-chrome");
  if ((await wrap.count()) === 0) {
    return;
  }
  if ((await wrap.getAttribute("open")) == null) {
    await wrap.locator("summary").first().click();
  }
  await expect(wrap).toHaveAttribute("open", "");
}

async function waitForMapState(page: Page, state: "sufficient") {
  const map = page.getByTestId("map-stage");
  await expect(map).toHaveAttribute("data-map-state", state, { timeout: 45_000 });
  return map;
}

async function selectZone(page: Page) {
  const inventory = page.getByTestId("area-context-inventory");
  if ((await inventory.count()) > 0 && (await inventory.getAttribute("open")) == null) {
    await inventory.locator("summary").first().click();
    await expect(inventory).toHaveAttribute("open", "");
  }
  const contextList = page.getByTestId("area-context-list");
  const contextButton = contextList.locator("tbody button").first();
  if ((await contextList.count()) > 0 && (await contextButton.count()) > 0) {
    await expect(contextButton).toBeVisible();
    await contextButton.click();
    return;
  }

  const wrap = page.getByTestId("map-interaction-list-wrap");
  if ((await wrap.count()) > 0) {
    await openMapAdvancedChrome(page);
    if ((await wrap.getAttribute("open")) == null) {
      await wrap.locator("summary").first().click();
      await expect(wrap).toHaveAttribute("open", "");
    }
  }
  const mapButton = page.getByTestId("map-interaction-list").locator("button").first();
  await expect(mapButton).toBeVisible();
  await mapButton.click();
}

test.describe("isolated HVA_PUBLIC_CONTEXT=1", () => {
  test.describe.configure({ timeout: 120_000 });
  test.use({ timezoneId: "America/Phoenix" });
  test.skip(!CONTEXT_ON, "skipped unless HVA_PUBLIC_CONTEXT=1");

  test("JudgeShell zone story on 2022-07-01 withheld context", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("judge-shell")).toBeVisible();
    await expect(page.getByRole("heading", { name: "HVA-Signal" })).toBeVisible();
    await expect(page.locator("[data-testid='command-center']")).toHaveCount(0);

    await fillAnalysisTime(page, INSUFFICIENT_TIME);
    await submitAnalysis(page);

    const map = await waitForMapState(page, "sufficient");
    await expect(map).toHaveAttribute("data-ranked-feature-count", "25");
    await expect(map).toHaveAttribute("data-geometry-feature-count", "25");
    await expect(page.getByTestId("happening-stamp")).toHaveText(
      "SPATIAL ORDERING WITHHELD",
    );

    const contextBand = page.getByTestId("area-context-band");
    await expect(contextBand).toBeVisible({ timeout: 45_000 });
    await expect(page.getByTestId("area-context-list")).toBeVisible();
    await expect(page.getByTestId("area-context-list-caption")).toHaveText(
      "Context and inventory values for each analysis area",
    );
    await expect(page.getByTestId("area-context-list-caption")).not.toContainText(
      "Thermal evidence values",
    );

    await selectZone(page);
    const story = page.getByTestId("selected-area-story");
    await expect(story).toBeVisible({ timeout: 30_000 });
    for (const question of STORY_QUESTIONS) {
      await expect(story).toContainText(question);
    }
    await expect(page.getByTestId("decision-direction")).toContainText("What to verify next");

    await openEvidenceDisclosure(page);
    const signalB = page.getByTestId("signal-b-cached-panel");
    await expect(signalB).toBeVisible();
    await expect(page.getByTestId("signal-b-maturity")).toContainText(
      "CACHED EVIDENCE",
    );

    await expect(map).toHaveAttribute("data-map-state", "sufficient");
    await expect(map).toHaveAttribute("data-ranked-feature-count", "25");
    await expect(page.getByTestId("happening-stamp")).toHaveText(
      "SPATIAL ORDERING WITHHELD",
    );

    const incomeTab = page.locator('[data-testid="map-mode-tabs"] [data-mode="INCOME"]');
    if ((await incomeTab.count()) > 0) {
      await incomeTab.click();
      await expect(map).toHaveAttribute("data-map-mode", "INCOME");
      await expect(page.getByTestId("map-mode-legend")).toHaveAttribute("data-mode", "INCOME");
      await expect(page.getByTestId("happening-stamp")).toHaveText(
        "SPATIAL ORDERING WITHHELD",
      );
    }

    const blob = ((await page.locator("body").innerText()) ?? "").toLowerCase();
    expect(blob, "TEST_ONLY").not.toContain("test_only");
    expect(blob, "NO COOLING SITE").not.toContain("no cooling site");
    expect(blob, "Thermal evidence values caption").not.toContain(
      "thermal evidence values",
    );
  });
});
