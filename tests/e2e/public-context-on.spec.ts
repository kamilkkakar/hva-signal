import { expect, test, type Page } from "@playwright/test";

const CONTEXT_ON = /^(1|true|yes|on)$/i.test(
  (process.env.HVA_PUBLIC_CONTEXT ?? "").trim(),
);

const INSUFFICIENT_TIME = "2022-07-01T03:00";

const STORY_QUESTIONS = [
  "WHAT ARE THERMAL CONDITIONS HERE?",
  "WHAT MAKES THIS AREA DIFFERENT?",
  "WHAT SUPPORT IS IDENTIFIED NEARBY?",
  "WHAT SHOULD BE VERIFIED BEFORE ACTION?",
] as const;

async function fillAnalysisTime(page: Page, value: string) {
  const input = page.locator('input[name="analysis_time"]');
  await input.fill(value);
  await expect(input).toHaveValue(value);
}

async function submitAnalysis(page: Page) {
  await page.getByRole("button", { name: "Submit analysis" }).click();
}

async function waitForMapState(page: Page, state: "insufficient") {
  const map = page.getByTestId("map-stage");
  await expect(map).toHaveAttribute("data-map-state", state, { timeout: 45_000 });
  return map;
}

async function selectZone(page: Page) {
  const contextList = page.getByTestId("area-context-list");
  const contextButton = contextList.locator("tbody button").first();
  if ((await contextList.count()) > 0 && (await contextButton.count()) > 0) {
    await expect(contextButton).toBeVisible();
    await contextButton.click();
    return;
  }

  const wrap = page.getByTestId("map-interaction-list-wrap");
  if ((await wrap.count()) > 0 && (await wrap.getAttribute("open")) == null) {
    await wrap.locator("summary").first().click();
    await expect(wrap).toHaveAttribute("open", "");
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

    const map = await waitForMapState(page, "insufficient");
    await expect(map).toHaveAttribute("data-ranked-feature-count", "0");
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

    const signalB = page.getByTestId("signal-b-cached-panel");
    await expect(signalB).toBeVisible();
    await expect(page.getByTestId("signal-b-maturity")).toContainText(
      "CACHED EVIDENCE",
    );
    await expect(page.getByTestId("story-thermal-b")).toContainText(
      "CACHED EVIDENCE",
    );

    await expect(map).toHaveAttribute("data-map-state", "insufficient");
    await expect(map).toHaveAttribute("data-ranked-feature-count", "0");
    await expect(page.getByTestId("happening-stamp")).toHaveText(
      "SPATIAL ORDERING WITHHELD",
    );

    const incomeTab = page.locator('[data-testid="map-mode-tabs"] [data-mode="INCOME"]');
    if ((await incomeTab.count()) > 0) {
      await incomeTab.click();
      await expect(map).toHaveAttribute("data-map-mode", "INCOME");
      await expect(map).toHaveAttribute("data-ranked-feature-count", "0");
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
