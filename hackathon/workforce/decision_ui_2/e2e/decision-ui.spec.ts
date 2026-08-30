import { expect, test } from "@playwright/test";

const FORBIDDEN = [
  "q_A",
  "Decision 8",
  "FortyGuard",
  "WBGT",
  "HeatDose",
  "AfterHeat",
  "probability",
  "low risk",
  "high risk",
  "current conditions",
];

test.describe("Decision UI 2.0", () => {
  test("question-first public face stays pending and contained", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("decision-shell")).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Decision questions" })).toBeVisible();
    await expect(page.getByRole("heading", { name: /What is happening at this time/i })).toBeVisible();

    const body = (await page.locator("body").innerText()).toLowerCase();
    for (const token of FORBIDDEN) {
      expect(body, token).not.toContain(token.toLowerCase());
    }
    expect(body).not.toContain("+0.8");
    expect(body).not.toContain("91 / 92");
    expect(body).toContain("awaiting temporal program");

    const overflow = await page.evaluate(() => {
      const root = document.documentElement;
      return {
        scrollWidth: root.scrollWidth,
        clientWidth: root.clientWidth,
      };
    });
    expect(overflow.scrollWidth - overflow.clientWidth).toBeLessThanOrEqual(1);

    await page.locator('[data-area-id="area-6"]').click();
    await expect(page.getByTestId("selected-area")).toContainText("Analysis area 6");
    await expect(page.getByTestId("chart-hourly_curve")).toContainText("Analysis area 6");

    await page.getByTestId("question-after-intervention").click();
    await expect(page.getByTestId("intervention-panel")).toContainText("Not a treatment result");

    await page.getByTestId("question-capacity-to-cope").click();
    await expect(page.getByTestId("vulnerability-panel")).toContainText("Not a score");

    await page.getByRole("button", { name: "Why?" }).click();
    await expect(page.getByTestId("method-panel")).toContainText("Each question names a comparison");
  });

  test("desktop map modes expose legend chrome", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("map-mode").selectOption("year_over_year");
    const legend = page.getByTestId("map-legend");
    await expect(legend).toContainText("Year-over-year");
    await expect(legend).toContainText("Unit");
    await expect(legend).toContainText("Period");
    await expect(legend).toContainText("Baseline");
  });
});
