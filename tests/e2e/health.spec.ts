import { test, expect } from "@playwright/test";

const apiBase = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

test("web shell loads command center", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "HVA-Signal" }),
  ).toBeVisible();
  await expect(page.getByTestId("source-banner")).toContainText("UNAVAILABLE");
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
