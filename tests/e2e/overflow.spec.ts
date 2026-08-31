import { expect, test, type Page } from "@playwright/test";

const VIEWPORTS = [1920, 1440, 1280, 1024] as const;

async function pageBox(page: Page) {
  return page.evaluate(() => {
    const root = document.documentElement;
    const shell =
      document.querySelector("[data-testid='workspace']") ??
      document.querySelector(".ws") ??
      document.querySelector(".shell");
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
  if (box.shellClient > 0) {
    expect(box.shellScroll, `${label} shell`).toBeLessThanOrEqual(
      box.shellClient + 1,
    );
  }
}

test.describe("result layout overflow", () => {
  test("idle landing has no page-level horizontal scroll", async ({ page }) => {
    for (const width of VIEWPORTS) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/");
      await expect(
        page.getByRole("heading", { name: /HVA-SIGNAL/i }),
      ).toBeVisible();
      expectNoPageScroll(await pageBox(page), `${width} idle`);
    }
  });

  test("loaded Phoenix workspace stays inside 1024–1920 without page scroll", async ({
    page,
  }) => {
    test.setTimeout(90_000);
    await page.setViewportSize({ width: 1024, height: 900 });
    await page.goto("/");
    await expect(page.getByTestId("workspace")).toBeVisible();
    await expect(page.getByTestId("map-stage")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("map-stage")).toHaveAttribute(
      "data-map-state",
      "sufficient",
      { timeout: 60_000 },
    );

    for (const width of VIEWPORTS) {
      await page.setViewportSize({ width, height: 900 });
      await expect(page.getByTestId("workspace")).toBeVisible();
      expectNoPageScroll(await pageBox(page), `${width} result`);
    }
  });
});
