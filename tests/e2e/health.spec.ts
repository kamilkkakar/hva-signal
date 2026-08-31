import { test, expect } from "@playwright/test";

const apiBase = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

test("web workspace loads with HVA-Signal heading and published observation", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /HVA-SIGNAL/i }),
  ).toBeVisible();
  await expect(page.getByTestId("workspace")).toBeVisible();
  await expect(page.getByTestId("explore-city")).toBeVisible();
  const provenance = page.getByTestId("observation-provenance");
  await expect(provenance).toBeVisible({ timeout: 15_000 });
  await expect(provenance).toContainText("Published");
});

test("API /health and /ready respond in replay mode", async ({ request }) => {
  const health = await request.get(`${apiBase}/health`);
  expect(health.ok()).toBeTruthy();
  await expect(health.json()).resolves.toEqual({ status: "ok" });

  const ready = await request.get(`${apiBase}/ready`);
  expect(ready.ok()).toBeTruthy();
  const body = await ready.json();
  expect(body.status).toBe("ready");
  expect(body.data_mode).toBe("replay");
});
