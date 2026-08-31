import { expect, test, type Page } from "@playwright/test";

const VIEWPORTS = [1920, 1440, 1280, 1024] as const;

async function pageBox(page: Page) {
  return page.evaluate(() => {
    const root = document.documentElement;
    const shell = document.querySelector(".shell");
    return {
      rootScroll: root.scrollWidth,
      rootClient: root.clientWidth,
      bodyScroll: document.body.scrollWidth,
      bodyClient: document.body.clientWidth,
      shellScroll: shell instanceof HTMLElement ? shell.scrollWidth : 0,
      shellClient: shell instanceof HTMLElement ? shell.clientWidth : 0,
    };
  });
}

function expectNoPageScroll(
  box: Awaited<ReturnType<typeof pageBox>>,
  label: string,
) {
  expect(box.rootScroll, `${label} documentElement`).toBeLessThanOrEqual(
    box.rootClient + 1,
  );
  expect(box.bodyScroll, `${label} body`).toBeLessThanOrEqual(box.bodyClient + 1);
  expect(box.shellScroll, `${label} .shell`).toBeLessThanOrEqual(
    box.shellClient + 1,
  );
}

test.describe("result layout overflow", () => {
  test("idle landing has no page-level horizontal scroll", async ({ page }) => {
    for (const width of VIEWPORTS) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/");
      await expect(
        page.getByRole("heading", { name: "HVA-Signal" }),
      ).toBeVisible();
      expectNoPageScroll(await pageBox(page), `${width} idle`);
    }
  });

  test("completed Decision 8 result stays inside 1024–1920 without page scroll", async ({
    page,
    request,
  }) => {
    test.setTimeout(90_000);
    await page.setViewportSize({ width: 1024, height: 900 });
    await page.goto("/");
    const demo = page.getByTestId("demo-controls");
    if ((await demo.count()) > 0) {
      await demo.evaluate((node) => {
        if (node instanceof HTMLDetailsElement) {
          node.open = true;
        }
      });
    }
    await page.getByRole("button", { name: "Submit analysis" }).click();

    const details = page.getByTestId("analysis-detail");
    await expect(details).toBeAttached({ timeout: 45_000 });
    if ((await details.getAttribute("open")) == null) {
      await page.getByTestId("advanced-technical-details").click();
    }
    const panel = page.getByTestId("decision8-evidence-panel");
    await expect(panel).toBeVisible({ timeout: 45_000 });
    await expect(page.getByTestId("analysis-detail")).toHaveAttribute("open", "");
    await expect(page.getByTestId("decision8-zone-geometry")).toContainText(
      "US_CENSUS_TIGERLINE",
    );
    await expect(page.getByTestId("decision8-geometry-token-copy")).toBeVisible();
    await expect(page.getByTestId("job-id-copy")).toBeVisible();

    const apiBase = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";
    expect(apiBase).toBeTruthy();
    expect(request).toBeTruthy();

    for (const width of VIEWPORTS) {
      await page.setViewportSize({ width, height: 900 });
      await expect(panel).toBeVisible();
      expectNoPageScroll(await pageBox(page), `${width} result`);
      const decision = page.getByRole("complementary", { name: "Decision panel" });
      const decisionBox = await decision.evaluate((node) => ({
        scroll: node.scrollWidth,
        client: node.clientWidth,
      }));
      expect(decisionBox.scroll, `${width} decision rail`).toBeLessThanOrEqual(
        decisionBox.client + 1,
      );
    }
  });
});
